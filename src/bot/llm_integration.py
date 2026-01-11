"""Integration layer between Telegram bot and LLM API."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..llm import (
    YandexLLMClient,
    RickMode,
    build_rick_prompt,
    ResponseProcessor,
)
from ..llm.models import ModelName
from ..llm.response_parsers import (
    ClaudeResponseParser,
    GPTResponseParser,
    GrokResponseParser,
)
from ..llm.modes import build_mode_prompt
from .state_manager import StateManager
from .mcp_manager import MCPManager
from ..config import get_logger

logger = get_logger(__name__)


class LLMIntegration:
    """Integration handler for LLM and bot state."""

    def __init__(
        self,
        llm_client: YandexLLMClient,
        state_manager: StateManager,
        response_processor: ResponseProcessor,
        mcp_managers: Optional[List[MCPManager]] = None,
    ):
        """Initialize LLM integration.

        Args:
            llm_client: Yandex LLM API client
            state_manager: User state manager
            response_processor: Response processor
            mcp_managers: List of MCP managers for tool integration (optional)
        """
        self.llm_client = llm_client
        self.state_manager = state_manager
        self.response_processor = response_processor
        self.mcp_managers = mcp_managers or []
        logger.info(
            "LLMIntegration initialized (MCP count: %s)",
            len(self.mcp_managers),
        )
    
    async def process_message(self, user_id: int, message: str) -> str:
        """Process user message and generate response.

        Args:
            user_id: Telegram user ID
            message: User message text

        Returns:
            Generated response text

        Raises:
            Exception: If LLM API call fails
        """
        # Get user state and temperature (async)
        user_state = await self.state_manager.get_user_state(user_id)
        user_temperature = user_state.temperature

        logger.info(f"Processing message for user {user_id} with temperature {user_temperature}")

        # Check if summarization is needed
        await self._check_and_perform_summarization(user_id, user_state)

        # Try to enrich request with RAG context (always attempt; filtering controlled separately)
        rag_context_block, rag_sources = await self._retrieve_rag_context(
            user_state,
            message
        )

        enriched_message = message
        if rag_context_block:
            enriched_message = (
                "User question:\n"
                f"{message}\n\n"
                "Retrieved context (RAG, relevance sorted):\n"
                f"{rag_context_block}\n\n"
                "Используй контекст только если он релевантен вопросу. "
                "Разделяй факты из контекста и из вопроса."
            )

        # Build prompt with NORMAL mode (only mode available)
        system_prompt, user_message = build_mode_prompt(RickMode.NORMAL, enriched_message)

        # Build complete prompt structure with conversation history
        messages = build_rick_prompt(
            user_message=user_message,
            system_prompt=system_prompt,
            conversation_history=user_state.conversation_history
        )

        initialized_managers = self._get_initialized_managers()

        tools: Optional[List[Dict[str, Any]]] = None
        tool_name_to_manager: Dict[str, MCPManager] = {}

        if initialized_managers:
            tools = []
            for manager in initialized_managers:
                manager_tools = manager.get_tools_for_api()
                for tool in manager_tools:
                    tool_name = tool.get("function", {}).get("name")
                    if not tool_name or tool_name in tool_name_to_manager:
                        continue
                    tool_name_to_manager[tool_name] = manager
                    tools.append(tool)

            logger.info(
                "Aggregated %s tool(s) from %s MCP manager(s)",
                len(tools),
                len(initialized_managers),
            )
        else:
            logger.warning("No initialized MCP managers - tools are disabled")

        tools = []
        # Send to LLM API with user-specific temperature
        try:
            # Tool calling loop (max 3 iterations)
            max_iterations = 3
            tool_call_history = []

            for iteration in range(max_iterations):
                logger.debug(f"LLM iteration {iteration + 1}/{max_iterations}")

                response = await self.llm_client.send_prompt(
                    messages,
                    temperature=user_temperature,
                    model=user_state.model,
                    tools=tools,
                    tool_choice="auto" if tools else "none",
                )

                # Extract text from response
                self.response_processor.parser = self._select_parser(user_state.model)
                response_text = self.response_processor.extract_text(response)
                
                # Handle None content (can happen with tool_calls)
                if response_text is None:
                    response_text = ""

                # Record metadata for statistics
                metadata = self.response_processor.get_metadata(response)
                if metadata: 
                    logger.debug(f"Response metadata for user {user_id}: {metadata}")
                    usage = metadata.get("usage", {})
                    input_tokens = usage.get("input_tokens", 0) or 0
                    cache_read_tokens = usage.get("input_cache_read_tokens", 0) or 0
                    total_input_tokens = input_tokens + cache_read_tokens
                    output_tokens = usage.get("output_tokens", 0)
                    cost = metadata.get("cost", 0.0)

                    if total_input_tokens > 0 or output_tokens > 0 or cost > 0:
                        await user_state.add_usage_stats(total_input_tokens, output_tokens, cost)

                # Check if LLM wants to call tools
                logger.debug(
                    "Checking for tool calls: managers=%s, tools_provided=%s",
                    len(initialized_managers),
                    bool(tools),
                )

                tool_calls: List[Dict[str, Any]] = []
                if initialized_managers and tools:
                    parser_manager = initialized_managers[0]
                    tool_calls = parser_manager.extract_tool_calls_from_response(response)
                    # Keep only tool calls that we can route
                    tool_calls = [
                        tc for tc in tool_calls if tc.get("name") in tool_name_to_manager
                    ]
                    logger.debug(f"Extracted {len(tool_calls)} tool call(s) from response")

                    if tool_calls:
                        logger.info(f"LLM requested {len(tool_calls)} tool call(s)")
                        logger.debug(f"Response content before tool execution: '{response_text}'")

                        # Add assistant message with tool calls to history
                        # Build tool_calls in API format for message history
                        assistant_tool_calls = []
                        for tc in tool_calls:
                            assistant_tool_calls.append({
                                "id": tc.get("id"),
                                "type": "function",
                                "function": {
                                    "name": tc["name"],
                                    "arguments": json.dumps(tc["arguments"]) if isinstance(tc["arguments"], dict) else tc["arguments"]
                                }
                            })
                        
                        assistant_message = {
                            "role": "assistant",
                            "content": response_text if response_text else None
                        }
                        if assistant_tool_calls:
                            assistant_message["tool_calls"] = assistant_tool_calls
                        
                        messages.append(assistant_message)
                        logger.debug(f"Added assistant message with {len(assistant_tool_calls)} tool_calls")

                        # Execute each tool and collect results
                        for tool_call in tool_calls:
                            tool_name = tool_call["name"]
                            tool_arguments = tool_call["arguments"]
                            tool_call_id = tool_call.get("id")

                            manager = tool_name_to_manager.get(tool_name)
                            if not manager:
                                logger.warning("No MCP manager found for tool %s", tool_name)
                                continue

                            logger.info(f"Executing tool: {tool_name}")

                            # Execute tool
                            tool_result = await manager.call_tool(
                                tool_name,
                                tool_arguments
                            )

                            # Format result text
                            if tool_result.get("success"):
                                result_content = str(tool_result.get("result", ""))
                            else:
                                result_content = f"Error: {tool_result.get('error', 'Unknown error')}"

                            # Add to tool call history for summary
                            tool_call_history.append({
                                "name": tool_name,
                                "arguments": tool_arguments,
                                "result": result_content
                            })

                            # Add tool result message in OpenAI format
                            tool_message = {
                                "role": "tool",
                                "tool_call_id": tool_call_id,
                                "content": result_content
                            }
                            
                            messages.append(tool_message)
                            logger.debug(f"Added tool result message: role=tool, tool_call_id={tool_call_id}")

                        # Continue to next iteration
                        continue
                    else:
                        logger.debug("No tool_calls found in response")
                else:
                    if not initialized_managers:
                        logger.debug("No initialized MCP managers available")
                    elif not tools:
                        logger.debug("No tools provided to LLM")

                # No tool call - this is the final response
                formatted_response = response_text.strip() if response_text else ""
                
                # If response is empty and we have no tool history, something went wrong
                if not formatted_response and not tool_call_history:
                    logger.warning(f"Empty response received for user {user_id}")
                    formatted_response = "Извините, я получил пустой ответ. Попробуйте еще раз."

                # Add tool call summary if any tools were used
                if tool_call_history:
                    tool_summary = "\n\n🔧 Tools used:\n"
                    for i, call_data in enumerate(tool_call_history, 1):
                        tool_name = call_data["name"]
                        tool_summary += f"{i}. {tool_name}\n"
                    formatted_response = formatted_response + tool_summary

                metadata_block = (
                    self._format_metadata(metadata, self.llm_client.max_tokens)
                    if metadata
                    else None
                )

                sources_block = ""
                if rag_sources:
                    unique_sources: List[str] = []
                    seen_sources: set[str] = set()
                    for src in rag_sources:
                        if not src:
                            continue
                        normalized = str(Path(src).expanduser().resolve(strict=False))
                        if normalized in seen_sources:
                            continue
                        seen_sources.add(normalized)
                        unique_sources.append(normalized)

                    if unique_sources:
                        sources_lines = ["🔗 Источники:"]
                        sources_lines.extend(f"- {src}" for src in unique_sources)
                        sources_block = "\n".join(sources_lines)

                if sources_block:
                    formatted_response = f"{formatted_response}\n\n{sources_block}"

                if metadata_block:
                    formatted_response = f"{formatted_response}\n\n{metadata_block}"

                # Save messages to conversation history (async)
                await user_state.add_message("user", message)
                await user_state.add_message("assistant", response_text)

                return formatted_response

            # If we exhausted all iterations
            logger.warning(f"Max tool call iterations ({max_iterations}) reached for user {user_id}")
            return "Извините, я использовал слишком много инструментов. Попробуйте переформулировать вопрос."

        except Exception as e:
            logger.error(f"Failed to process message for user {user_id}: {e}", exc_info=True)
            raise
    
    async def reset_conversation(self, user_id: int):
        """Reset conversation state for user.

        Args:
            user_id: Telegram user ID
        """
        await self.state_manager.reset_user_state(user_id)
        logger.info(f"Conversation reset for user {user_id}")
    
    async def cleanup(self):
        """Cleanup resources."""
        await self.llm_client.close()
        for manager in self.mcp_managers:
            await manager.cleanup()
        logger.info("LLMIntegration cleanup completed")

    def get_all_tools(self) -> List[Dict[str, Any]]:
        """Return aggregated tools from all initialized MCP managers."""
        result: List[Dict[str, Any]] = []
        seen: set[str] = set()
        for manager in self._get_initialized_managers():
            for tool in manager.tools:
                name = tool.get("name")
                if not name or name in seen:
                    continue
                seen.add(name)
                result.append(tool)
        return result

    def _format_metadata(
        self,
        metadata: Optional[Dict[str, Any]],
        max_output_tokens: Optional[int],
    ) -> Optional[str]:
        """Render metadata as monospace block for user output."""
        if not metadata or not isinstance(metadata, dict):
            return None

        lines = []
        usage = metadata.get("usage") or {}
        output_pct = None

        if isinstance(usage, dict):
            input_tokens = usage.get("input_tokens") + usage.get("input_cache_read_tokens", 0)
            output_tokens = usage.get("output_tokens")

            if input_tokens is not None:
                lines.append(f"usage.input_tokens = {input_tokens}")
            if output_tokens is not None:
                lines.append(f"usage.output_tokens = {output_tokens}")
                if max_output_tokens:
                    output_pct = (output_tokens / max_output_tokens) * 100

        if output_pct is not None:
            lines.append(
                f"token limit = {output_pct:.2f}% (limit = {max_output_tokens})"
            )

        if metadata.get("cost") is not None:
            cost_value = metadata.get("cost")
            if isinstance(cost_value, (int, float)):
                # Format to avoid scientific notation, show up to 7 decimal places
                formatted_cost = f"{cost_value:.7f}".rstrip('0').rstrip('.')
                lines.append(f"cost = {formatted_cost}")
            else:
                lines.append(f"cost = {cost_value}")

        if metadata.get("time_ms") is not None:
            lines.append(f"time_ms = {metadata.get('time_ms')}")

        if not lines:
            return None
        return "```\n" + "\n".join(lines) + "\n```"

    async def _check_and_perform_summarization(self, user_id: int, user_state):
        """Check if summarization is needed and perform it if required.

        Args:
            user_id: Telegram user ID
            user_state: User state object
        """
        # Check if summarization is enabled
        if not user_state.summarization_enabled:
            return

        # Count user messages (exclude system/assistant messages for counting)
        user_messages = [msg for msg in user_state.conversation_history if msg.get("role") == "user" or msg.get("role") == "assistant"]

        # Only summarize if we have 10+ user messages
        if len(user_messages) < 10:
            return

        logger.info(f"Performing summarization for user {user_id} with {len(user_messages)} user messages")

        try:
            # Create summarization prompt
            summarization_prompt = self._create_summarization_prompt(user_state.conversation_history)

            # Send summarization request to LLM
            summarization_messages = [
                {"role": "system", "content": """
# ROLE
You are a "Context Compression Engine" designed for LLM memory management. Your goal is to analyze a raw dialogue history between a User and an AI Assistant and convert it into a concise, highly structured summary.

# OBJECTIVE
Reduce the token count of the conversation by 70-90% while retaining 100% of the semantic meaning, critical facts, constraints, and the current state of tasks. The output will be used as "Memory" for the next interaction.

# COMPRESSION ALGORITHM
1. **Filter Noise:** Remove all phatic communication (greetings, "thank you", "okay", "I understand", apologies).
2. **Track State:** Identify the user's main goal and how it evolved. If the user changed requirements midway, keep ONLY the final requirements.
3. **Extract Entities:** Preserve specific data points strictly (Names, Dates, Code Snippets concepts, API keys, Style preferences).
4. **Abstract Logic:** Summarize long explanations. Instead of repeating an explanation, state: "Assistant explained [Topic]."

# CRITICAL RETENTION RULES
- **Do NOT** summarize the AI's personality (e.g., "The AI was helpful"). Focus on the *information* exchanged.
- **Do NOT** use vague language like "They discussed various topics." Be specific: "Discussed Python optimization via Vectorization."
- **ALWAYS** preserve code logic or math formulas if they are essential to the next step.
- **ALWAYS** preserve user constraints (e.g., "User wants response in JSON only").

# OUTPUT FORMAT
Generate a summary in the following structure (in Russian):

**1. Текущий контекст:**
[A dense paragraph summarizing the narrative flow: What did the user ask? What was solved? What is the current focus?]

**2. Факты и Переменные:**
- [Key: Value] (e.g., User Name, OS, Tone Preference, Specific Numbers)

**3. Активные ограничения:**
- [List specific negative or positive constraints currently active]

**4. Статус задачи:**
[PENDING / SOLVED] - [Brief description of the next expected step]

# INPUT PROCESSING
The history allows for corrections. If the user said "Make it blue", then "No, red", the summary must state: "Color preference: Red".

START COMPRESSION.
                """},
                {"role": "user", "content": summarization_prompt}
            ]

            response = await self.llm_client.send_prompt(
                summarization_messages,
                temperature=0.3,  # Lower temperature for consistent summaries
                model=user_state.model,
            )

            # Extract summary text
            self.response_processor.parser = self._select_parser(user_state.model)
            summary_text = self.response_processor.extract_text(response)

            # Record summarization statistics (async)
            metadata = self.response_processor.get_metadata(response)
            if metadata:
                usage = metadata.get("usage", {})
                input_tokens = usage.get("input_tokens", 0) or 0
                cache_read_tokens = usage.get("input_cache_read_tokens", 0) or 0
                total_input_tokens = input_tokens + cache_read_tokens
                output_tokens = usage.get("output_tokens", 0)
                cost = metadata.get("cost", 0.0)

                await user_state.add_summarization_stats(total_input_tokens, output_tokens, cost)
                logger.debug(f"Recorded summarization stats for user {user_id}: input={total_input_tokens}, output={output_tokens}, cost={cost}")

            # Perform summarization using StateManager (handles DB operations)
            await self.state_manager.perform_summarization(user_id, f"[CHAT SUMMARY: {summary_text}]\n\nContinuing our conversation...")

            logger.info(f"Summarization completed for user {user_id}")

        except Exception as e:
            logger.error(f"Failed to perform summarization for user {user_id}: {e}")
            # Continue with normal processing if summarization fails

    def _create_summarization_prompt(self, conversation_history) -> str:
        """Create a summarization prompt from conversation history.

        Args:
            conversation_history: List of conversation messages

        Returns:
            Summarization prompt string
        """
        # Format conversation history for summarization
        conversation_text = ""
        for msg in conversation_history:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if role == "user":
                conversation_text += f"User: {content}\n"
            elif role == "assistant":
                conversation_text += f"Assistant: {content}\n"

        prompt = f"""Please summarize the following conversation between a user and an AI assistant. 
Keep the summary concise but comprehensive, capturing the main topics, key points, and context. 
Focus on what was discussed and any important conclusions or ongoing threads.

Conversation:
{conversation_text}

Summary:"""

        return prompt

    def _get_initialized_managers(self) -> List[MCPManager]:
        """Return only initialized MCP managers."""
        return [m for m in self.mcp_managers if m and m.is_initialized]

    def _get_rag_manager(self) -> Optional[MCPManager]:
        """Return initialized MCP manager that exposes search_articles tool."""
        for manager in self._get_initialized_managers():
            for tool in manager.tools:
                if tool.get("name") == "search_articles":
                    return manager
        return None

    async def _retrieve_rag_context(
        self,
        user_state,
        query: str
    ) -> tuple[Optional[str], List[str]]:
        """Fetch RAG context via MCP search_articles tool.

        Returns:
            Tuple of formatted context block (or None) and list of article paths.
        """
        user_id = getattr(user_state, "user_id", None)
        rag_manager = self._get_rag_manager()
        if not rag_manager:
            logger.debug("RAG requested but no RAG MCP manager is initialized")
            return None, []

        rag_filter_enabled = getattr(user_state, "rag_filter_enabled", False)
        similarity_threshold = getattr(user_state, "rag_similarity_threshold", 0.3)

        try:
            result = await rag_manager.call_tool(
                "search_articles",
                {"query": query, "top_k": 15},
                timeout=20.0,
            )
            if not result.get("success"):
                logger.warning(f"RAG tool failed for user {user_id}: {result.get('error')}")
                return None, []

            raw_text = result.get("result") or ""
            data = json.loads(raw_text)
            hits = data.get("results") if isinstance(data, dict) else None
            if not hits:
                logger.info("RAG returned no results")
                return None, []

            def _safe_similarity(hit: Dict[str, Any]) -> float:
                """Return similarity with fallbacks (rerank_score -> similarity -> score)."""
                keys = ("rerank_score", "similarity", "score")
                for key in keys:
                    value = hit.get(key)
                    if value is None:
                        continue
                    try:
                        return float(value)
                    except (TypeError, ValueError):
                        continue
                return 0.0

            sorted_hits = sorted(hits, key=_safe_similarity, reverse=True)
            total_hits = len(sorted_hits)

            if rag_filter_enabled:
                filtered_hits = [
                    hit for hit in sorted_hits if _safe_similarity(hit) >= similarity_threshold
                ]
            else:
                filtered_hits = sorted_hits

            dropped_hits = total_hits - len(filtered_hits)

            if not filtered_hits:
                logger.info(
                    "RAG filter removed all results for user %s "
                    "(threshold=%.3f, total_hits=%s)",
                    user_id,
                    similarity_threshold,
                    total_hits,
                )
                return None, []

            formatted_lines = []
            source_paths: List[str] = []
            for idx, hit in enumerate(filtered_hits, 1):
                text = hit.get("text", "").strip()
                source = hit.get("source_path") or "unknown_source"
                source_paths.append(source)
                chunk_idx = hit.get("chunk_idx")
                similarity = _safe_similarity(hit)
                suffix = f" (chunk {chunk_idx})" if chunk_idx is not None else ""
                formatted_lines.append(
                    f"{idx}. [{source}{suffix}] (sim={similarity:.3f}) {text}"
                )

            context_block = "\n".join(formatted_lines)

            logger.info(
                "RAG stats for user %s: filter=%s, threshold=%.3f, "
                "total=%s, kept=%s, dropped=%s, context_len=%s",
                user_id,
                rag_filter_enabled,
                similarity_threshold,
                total_hits,
                len(filtered_hits),
                dropped_hits,
                len(context_block),
            )

            unique_sources: List[str] = []
            seen_sources: set[str] = set()
            for path in source_paths:
                normalized = str(Path(path).expanduser().resolve(strict=False))
                if normalized in seen_sources:
                    continue
                seen_sources.add(normalized)
                unique_sources.append(normalized)

            return context_block, unique_sources
        except Exception as e:
            logger.warning(f"Failed to retrieve RAG context: {e}", exc_info=True)
            return None, []

    @staticmethod
    def _select_parser(model: ModelName) -> Any:
        """Select parser based on model."""
        model_name = model.value if isinstance(model, ModelName) else str(model)
        lower_name = model_name.lower()

        if "claude" in lower_name:
            return ClaudeResponseParser()
        if "grok" in lower_name:
            return GrokResponseParser()
        return GPTResponseParser()

