"""Daily GitHub summary manager for automated activity reports."""

import json
from datetime import datetime
from typing import Dict, Any, Optional, List

from ..config import get_logger
from ..llm.prompts import build_daily_summary_prompt
from ..llm.response_parsers import _unwrap_response

logger = get_logger(__name__)


class DailySummaryManager:
    """Manager for daily GitHub activity summaries."""

    def __init__(self, mcp_manager, llm_integration, db_manager, bot):
        """Initialize DailySummaryManager.

        Args:
            mcp_manager: MCPManager instance for GitHub API calls
            llm_integration: LLMIntegration instance for summary generation
            db_manager: DatabaseManager instance for user settings
            bot: Telegram Bot instance for sending messages
        """
        self.mcp_manager = mcp_manager
        self.llm_integration = llm_integration
        self.db_manager = db_manager
        self.bot = bot
        logger.info("DailySummaryManager initialized")

    def _filter_events_by_date(
        self, events: List[Dict[str, Any]], target_date: datetime
    ) -> List[Dict[str, Any]]:
        """Filter events to only include those from target date.

        Args:
            events: List of GitHub events
            target_date: Target date to filter for

        Returns:
            Filtered list of events
        """
        filtered = []
        target_date_str = target_date.date().isoformat()

        for event in events:
            event_date = event.get("created_at", "")
            # Extract date from ISO timestamp (e.g., "2024-01-15T10:30:00Z")
            if event_date.startswith(target_date_str):
                filtered.append(event)

        logger.debug(
            f"Filtered {len(filtered)} events from {len(events)} for date {target_date_str}"
        )
        return filtered

    def _analyze_events(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze events and create summary statistics.

        Args:
            events: List of GitHub events

        Returns:
            Summary statistics
        """
        summary = {
            "total_events": len(events),
            "by_type": {},
            "repositories": set(),
            "commits_count": 0,
            "pull_requests": 0,
            "issues": 0,
            "comments": 0,
            "stars": 0,
            "forks": 0,
        }

        for event in events:
            event_type = event.get("type", "Unknown")

            # Count by type
            summary["by_type"][event_type] = summary["by_type"].get(event_type, 0) + 1

            # Track repositories
            repo_name = event.get("repo", {}).get("name", "")
            if repo_name:
                summary["repositories"].add(repo_name)

            # Analyze specific event types
            payload = event.get("payload", {})

            if event_type == "PushEvent":
                commits = payload.get("commits", [])
                summary["commits_count"] += len(commits)

            elif event_type == "PullRequestEvent":
                summary["pull_requests"] += 1

            elif event_type == "IssuesEvent":
                summary["issues"] += 1

            elif event_type in ["IssueCommentEvent", "CommitCommentEvent", "PullRequestReviewCommentEvent"]:
                summary["comments"] += 1

            elif event_type == "WatchEvent":
                summary["stars"] += 1

            elif event_type == "ForkEvent":
                summary["forks"] += 1

        # Convert set to list for JSON serialization
        summary["repositories"] = list(summary["repositories"])

        return summary

    def _format_activity_data(self, activity: Dict[str, Any]) -> str:
        """Format activity data for LLM prompt.

        Args:
            activity: Activity data dictionary

        Returns:
            Formatted string for prompt
        """
        if "error" in activity:
            return f"Ошибка при получении данных: {activity['error']}"

        summary = activity.get("summary", {})
        total_events = summary.get("total_events", 0)

        if total_events == 0:
            return "Никакой активности в GitHub за этот день не обнаружено."

        # Format summary text
        lines = [
            f"Всего событий: {total_events}",
            f"Репозиториев: {len(summary.get('repositories', []))}",
        ]

        # Add activity breakdown
        if summary.get("commits_count", 0) > 0:
            lines.append(f"Коммиты: {summary['commits_count']}")

        if summary.get("pull_requests", 0) > 0:
            lines.append(f"Pull Requests: {summary['pull_requests']}")

        if summary.get("issues", 0) > 0:
            lines.append(f"Issues: {summary['issues']}")

        if summary.get("comments", 0) > 0:
            lines.append(f"Комментарии: {summary['comments']}")

        if summary.get("stars", 0) > 0:
            lines.append(f"Звёзды: {summary['stars']}")

        if summary.get("forks", 0) > 0:
            lines.append(f"Форки: {summary['forks']}")

        # Add event types breakdown
        by_type = summary.get("by_type", {})
        if by_type:
            lines.append("\nТипы событий:")
            for event_type, count in sorted(
                by_type.items(), key=lambda x: x[1], reverse=True
            ):
                lines.append(f"  - {event_type}: {count}")

        # Add repositories list
        repos = summary.get("repositories", [])
        if repos:
            lines.append(f"\nРепозитории ({len(repos)}):")
            for repo in repos[:5]:  # Show top 5
                lines.append(f"  - {repo}")
            if len(repos) > 5:
                lines.append(f"  ... и ещё {len(repos) - 5}")

        return "\n".join(lines)

    async def generate_summary(
        self, username: str
    ) -> Optional[str]:
        """Generate summary text using LLM with tool calling support.

        Args:
            username: GitHub username
            activity: Activity data

        Returns:
            Generated summary text or None if failed
        """
        try:

            # Build prompt
            prompt = build_daily_summary_prompt(username)

            logger.debug(f"Generating summary for {username} with prompt length: {len(prompt)}")

            # Create temporary messages for generation
            messages = [{"role": "user", "content": prompt}]

            # Get tools from MCP manager if available
            tools = None
            if self.mcp_manager and self.mcp_manager.is_initialized:
                tools = self.mcp_manager.get_tools_for_api()
                logger.info(f"Using {len(tools) if tools else 0} MCP tools for summary generation")
            else:
                logger.debug("MCP not available - generating summary without tools")

            # Tool calling loop (max 10 iterations to allow for multiple tool calls)
            max_iterations = 10
            final_summary = None

            for iteration in range(max_iterations):
                logger.debug(f"Summary generation iteration {iteration + 1}/{max_iterations}")

                # Send to LLM with tools
                response = await self.llm_integration.llm_client.send_prompt(
                    messages=messages,
                    temperature=0.7,
                    tools=tools,
                    tool_choice="auto" if tools else "none",
                )

                # Extract text from response
                logger.debug(f"Response keys: {response.keys()}")
                
                # Unwrap response (it might be wrapped under 'response' key)
                payload = _unwrap_response(response)
                logger.debug(f"After unwrap, payload keys: {payload.keys()}")
                
                response_text = None
                if "choices" in payload and len(payload["choices"]) > 0:
                    message = payload["choices"][0].get("message", {})
                    response_text = message.get("content")
                    logger.debug(f"Extracted content type: {type(response_text)}, length: {len(response_text) if response_text else 0}")
                    if response_text:
                        logger.debug(f"Content preview: {response_text[:200]}...")
                else:
                    logger.warning("No choices found in payload")

                # Handle None content (can happen with tool_calls only)
                if response_text is None:
                    response_text = ""
                    logger.debug("Content was None, set to empty string")

                # Check if LLM wants to call tools
                if self.mcp_manager and self.mcp_manager.is_initialized and tools:
                    tool_calls = self.mcp_manager.extract_tool_calls_from_response(response)
                    logger.debug(f"Extracted {len(tool_calls)} tool call(s) from response")

                    if tool_calls:
                        logger.info(f"LLM requested {len(tool_calls)} tool call(s) during summary generation")

                        # Add assistant message with tool calls to history
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

                            logger.info(f"Executing tool: {tool_name} with args: {tool_arguments}")

                            # Execute tool
                            tool_result = await self.mcp_manager.call_tool(
                                tool_name,
                                tool_arguments
                            )

                            # Format result text
                            if tool_result.get("success"):
                                result_content = str(tool_result.get("result", ""))
                            else:
                                result_content = f"Error: {tool_result.get('error', 'Unknown error')}"

                            logger.debug(f"Tool {tool_name} result: {result_content[:200]}...")

                            # Add tool result message in OpenAI format
                            tool_message = {
                                "role": "tool",
                                "tool_call_id": tool_call_id,
                                "content": result_content
                            }
                            messages.append(tool_message)
                            logger.debug(f"Added tool result message for tool_call_id: {tool_call_id}")

                        # Check if we're on the last iteration
                        if iteration == max_iterations - 1:
                            logger.warning(f"Tool calls executed on last iteration {iteration + 1}/{max_iterations}, may not get final response")
                        
                        # Continue to next iteration to get final response with tool results
                        continue

                # No more tool calls - we have final response
                final_summary = response_text
                logger.debug(f"Setting final_summary, type: {type(final_summary)}, length: {len(final_summary) if final_summary else 0}")
                logger.info(f"Successfully generated summary for {username} (after {iteration + 1} iteration(s))")
                break

            # Check if we got a final response (note: we check 'is not None' because empty string is valid but unlikely)
            if final_summary is not None and final_summary.strip():
                logger.debug(f"Returning final summary, length: {len(final_summary)}")
                return final_summary
            else:
                logger.error(f"Failed to generate summary - final_summary is {'None' if final_summary is None else 'empty string'}")
                logger.error(f"Loop completed after {max_iterations} iterations without valid response")
                return None

        except Exception as e:
            logger.error(f"Error generating summary for {username}: {e}", exc_info=True)
            return None

    async def send_daily_summary_to_user(self, user_id: int) -> bool:
        """Send daily summary to a specific user.

        Args:
            user_id: Telegram user ID

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get user's GitHub username
            github_username = await self.db_manager.get_github_username(user_id)

            if not github_username:
                logger.warning(f"User {user_id} has no GitHub username set")
                # Notify user
                await self.bot.send_message(
                    chat_id=user_id,
                    text="*urp* Не могу отправить саммари - у тебя не указан GitHub username.\n\n"
                    "Используй команду: /set_github_username <твой_username>",
                )
                return False

            logger.info(f"Generating daily summary for user {user_id} (@{github_username})")


            # Generate summary
            summary_text = await self.generate_summary(github_username)

            if not summary_text:
                logger.error("Failed to generate summary")
                await self.bot.send_message(
                    chat_id=user_id,
                    text="*urp* Что-то пошло не так при генерации саммари. Попробуй позже.",
                )
                return False

            # Send summary
            message = f"📊 **Ежедневное саммари GitHub активности**\n\n{summary_text}"

            await self.bot.send_message(chat_id=user_id, text=message)

            logger.info(f"Successfully sent daily summary to user {user_id}")
            return True

        except Exception as e:
            logger.error(
                f"Error sending daily summary to user {user_id}: {e}", exc_info=True
            )
            return False

    async def send_all_daily_summaries(self, context=None):
        """Send daily summaries to all users with enabled setting.

        This is the main job function called by JobQueue.

        Args:
            context: Telegram context (from JobQueue, optional)
        """
        logger.info("=" * 60)
        logger.info("Starting daily summary job")
        logger.info("=" * 60)

        try:
            # Get list of users with daily summary enabled
            user_ids = await self.db_manager.get_users_for_daily_summary()

            if not user_ids:
                logger.info("No users with daily summary enabled")
                return

            logger.info(f"Sending daily summaries to {len(user_ids)} users")

            # Send summaries
            success_count = 0
            fail_count = 0

            for user_id in user_ids:
                try:
                    success = await self.send_daily_summary_to_user(user_id)
                    if success:
                        success_count += 1
                    else:
                        fail_count += 1
                except Exception as e:
                    logger.error(f"Error sending to user {user_id}: {e}")
                    fail_count += 1

            logger.info("=" * 60)
            logger.info(f"Daily summary job completed: {success_count} sent, {fail_count} failed")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"Error in daily summary job: {e}", exc_info=True)

