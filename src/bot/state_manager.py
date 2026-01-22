"""User state management for conversation context."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from ..llm.modes import RickMode
from ..config import get_logger
from ..utils.database import DatabaseManager, UserSettings, Message

logger = get_logger(__name__)


@dataclass
class RequestUsageStats:
    """Usage statistics for a single request."""
    input_tokens: int = 0
    output_tokens: int = 0
    cost: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class UserState:
    """State for individual user conversation."""

    user_id: int
    current_mode: RickMode = RickMode.NORMAL
    temperature: float = 0.3
    last_activity: datetime = field(default_factory=datetime.now)
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    usage_stats: List[RequestUsageStats] = field(default_factory=list)
    summarization_enabled: bool = True
    summarization_stats: List[RequestUsageStats] = field(default_factory=list)

    # Database integration fields
    _settings_loaded: bool = field(default=False, init=False)
    _db_manager: Optional[DatabaseManager] = field(default=None, init=False)

    def set_db_manager(self, db_manager: DatabaseManager):
        """Set database manager for persistence."""
        self._db_manager = db_manager

    async def ensure_settings_loaded(self):
        """Ensure user settings are loaded from database."""
        if not self._settings_loaded and self._db_manager:
            try:
                db_settings = await self._db_manager.get_user_settings(self.user_id)
                self.temperature = db_settings.temperature
                self.summarization_enabled = db_settings.summarization_enabled
                self._settings_loaded = True
                logger.debug(f"Loaded settings for user {self.user_id} from database")
            except Exception as e:
                logger.error(f"Failed to load settings for user {self.user_id}: {e}")

    async def save_settings(self):
        """Save current settings to database."""
        if self._db_manager:
            try:
                settings = UserSettings(
                    user_id=self.user_id,
                    temperature=self.temperature,
                    summarization_enabled=self.summarization_enabled,
                )
                await self._db_manager.save_user_settings(settings)
                logger.debug(f"Saved settings for user {self.user_id} to database")
            except Exception as e:
                logger.error(f"Failed to save settings for user {self.user_id}: {e}")

    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.now()

    async def add_message(self, role: str, content: str):
        """Add message to conversation history and database.

        Args:
            role: Message role ('user' or 'assistant')
            content: Message content
        """
        self.conversation_history.append({"role": role, "content": content})

        # Save to database
        if self._db_manager:
            try:
                message = Message(
                    id=None,
                    user_id=self.user_id,
                    role=role,
                    content=content,
                    created_at=datetime.now()
                )
                await self._db_manager.save_message(message)
                logger.debug(f"Saved message for user {self.user_id} to database")
            except Exception as e:
                logger.error(f"Failed to save message for user {self.user_id}: {e}")

    async def load_conversation_history(self):
        """Load conversation history from database."""
        if self._db_manager:
            try:
                messages = await self._db_manager.get_user_messages(self.user_id)
                self.conversation_history = [
                    {"role": msg.role, "content": msg.content}
                    for msg in messages
                ]
                logger.debug(f"Loaded {len(messages)} messages for user {self.user_id} from database")
            except Exception as e:
                logger.error(f"Failed to load conversation history for user {self.user_id}: {e}")

    async def clear_history(self):
        """Clear conversation history and usage statistics."""
        self.conversation_history.clear()
        self.usage_stats.clear()
        self.summarization_stats.clear()

        # Note: Database messages are not cleared here - they persist for summarization

    async def add_usage_stats(self, input_tokens: int, output_tokens: int, cost: float):
        """Add usage statistics for a request.

        Args:
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens used
            cost: Cost of the request
        """
        self.usage_stats.append(RequestUsageStats(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost
        ))

        # Update database
        if self._db_manager:
            try:
                await self._db_manager.increment_chat_usage(self.user_id, input_tokens, output_tokens, cost)
                logger.debug(f"Updated chat usage stats for user {self.user_id}")
            except Exception as e:
                logger.error(f"Failed to update chat usage stats for user {self.user_id}: {e}")

    async def add_summarization_stats(self, input_tokens: int, output_tokens: int, cost: float):
        """Add usage statistics for a summarization request.

        Args:
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens used
            cost: Cost of the summarization request
        """
        self.summarization_stats.append(RequestUsageStats(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost
        ))

        # Update database
        if self._db_manager:
            try:
                await self._db_manager.increment_summarization_usage(self.user_id, input_tokens, output_tokens, cost)
                logger.debug(f"Updated summarization usage stats for user {self.user_id}")
            except Exception as e:
                logger.error(f"Failed to update summarization usage stats for user {self.user_id}: {e}")

    async def get_usage_stats(self) -> Dict[str, float]:
        """Get aggregated usage statistics for this user from database.

        Returns:
            Dictionary with total input_tokens, output_tokens, and cost
        """
        if self._db_manager:
            try:
                db_stats = await self._db_manager.get_usage_stats(self.user_id)
                return {
                    "input_tokens": db_stats.chat_input_tokens,
                    "output_tokens": db_stats.chat_output_tokens,
                    "cost": db_stats.chat_cost,
                    "requests_count": db_stats.requests_count,
                    "summarization_count": db_stats.summarization_count,
                    "summarization_input_tokens": db_stats.summarization_input_tokens,
                    "summarization_output_tokens": db_stats.summarization_output_tokens,
                    "summarization_cost": db_stats.summarization_cost,
                    # Combined totals
                    "total_input_tokens": db_stats.chat_input_tokens + db_stats.summarization_input_tokens,
                    "total_output_tokens": db_stats.chat_output_tokens + db_stats.summarization_output_tokens,
                    "total_cost": db_stats.chat_cost + db_stats.summarization_cost,
                    "total_requests": db_stats.requests_count + db_stats.summarization_count
                }
            except Exception as e:
                logger.error(f"Failed to get usage stats for user {self.user_id}: {e}")

        # Fallback to in-memory calculation
        total_input = sum(stat.input_tokens for stat in self.usage_stats)
        total_output = sum(stat.output_tokens for stat in self.usage_stats)
        total_cost = sum(stat.cost for stat in self.usage_stats)

        summarization_input = sum(stat.input_tokens for stat in self.summarization_stats)
        summarization_output = sum(stat.output_tokens for stat in self.summarization_stats)
        summarization_cost = sum(stat.cost for stat in self.summarization_stats)

        # Calculate totals combining regular and summarization usage
        total_all_input = total_input + summarization_input
        total_all_output = total_output + summarization_output
        total_all_cost = total_cost + summarization_cost
        total_all_requests = len(self.usage_stats) + len(self.summarization_stats)

        return {
            "input_tokens": total_input,
            "output_tokens": total_output,
            "cost": total_cost,
            "requests_count": len(self.usage_stats),
            "summarization_count": len(self.summarization_stats),
            "summarization_input_tokens": summarization_input,
            "summarization_output_tokens": summarization_output,
            "summarization_cost": summarization_cost,
            # Combined totals
            "total_input_tokens": total_all_input,
            "total_output_tokens": total_all_output,
            "total_cost": total_all_cost,
            "total_requests": total_all_requests
        }


class StateManager:
    """Manager for user conversation states."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None, cleanup_hours: int = 24):
        """Initialize state manager.

        Args:
            db_manager: Database manager for persistence
            cleanup_hours: Hours of inactivity before state cleanup
        """
        self._states: Dict[int, UserState] = {}
        self.db_manager = db_manager
        self.cleanup_hours = cleanup_hours
        logger.info(f"StateManager initialized (cleanup={cleanup_hours}h, db={db_manager is not None})")

    async def get_user_state(self, user_id: int) -> UserState:
        """Get or create user state with database integration.

        Args:
            user_id: Telegram user ID

        Returns:
            User state object
        """
        if user_id not in self._states:
            logger.info(f"Creating new state for user {user_id}")
            state = UserState(user_id=user_id)
            if self.db_manager:
                state.set_db_manager(self.db_manager)
                # Ensure user exists in database and load settings
                await self.db_manager.get_or_create_user(user_id)
                await state.ensure_settings_loaded()
                # Load conversation history
                await state.load_conversation_history()
            self._states[user_id] = state

        state = self._states[user_id]
        state.update_activity()
        return state
    
    async def get_user_temperature(self, user_id: int) -> float:
        """Get current temperature setting for user.

        Args:
            user_id: Telegram user ID

        Returns:
            Current temperature value (default: 0.3)
        """
        state = await self.get_user_state(user_id)
        return state.temperature

    async def set_user_temperature(self, user_id: int, temperature: float):
        """Set temperature for user.

        Args:
            user_id: Telegram user ID
            temperature: Temperature value (0.0-2.0)
        """
        if not (0.0 <= temperature <= 2.0):
            raise ValueError("Temperature must be between 0.0 and 2.0")

        state = await self.get_user_state(user_id)
        old_temperature = state.temperature
        state.temperature = temperature
        # Save settings to database
        await state.save_settings()
        logger.info(f"User {user_id} temperature changed: {old_temperature} -> {temperature}")

    async def get_user_summarization_enabled(self, user_id: int) -> bool:
        """Get summarization setting for user.

        Args:
            user_id: Telegram user ID

        Returns:
            True if summarization is enabled, False otherwise
        """
        state = await self.get_user_state(user_id)
        return state.summarization_enabled

    async def set_user_summarization_enabled(self, user_id: int, enabled: bool):
        """Set summarization setting for user.

        Args:
            user_id: Telegram user ID
            enabled: Whether to enable summarization
        """
        state = await self.get_user_state(user_id)
        old_enabled = state.summarization_enabled
        state.summarization_enabled = enabled
        # Save settings to database
        await state.save_settings()
        logger.info(f"User {user_id} summarization changed: {old_enabled} -> {enabled}")

    async def reset_user_state(self, user_id: int):
        """Reset state for user - clears memory and database.

        Args:
            user_id: Telegram user ID
        """
        # Delete all messages and reset usage stats from database
        if self.db_manager:
            try:
                await self.db_manager.delete_all_messages(user_id)
                await self.db_manager.reset_usage_stats(user_id)
                logger.debug(f"Deleted messages and reset stats for user {user_id} in database")
            except Exception as e:
                logger.error(f"Failed to reset user data in database for user {user_id}: {e}")

        # Reset in-memory state
        if user_id in self._states:
            logger.info(f"Resetting in-memory state for user {user_id}")
            self._states[user_id] = UserState(user_id=user_id)
            if self.db_manager:
                self._states[user_id].set_db_manager(self.db_manager)
        else:
            logger.debug(f"No in-memory state to reset for user {user_id}")

    async def clear_user_history(self, user_id: int):
        """Clear conversation history for user.

        Args:
            user_id: Telegram user ID
        """
        state = await self.get_user_state(user_id)
        await state.clear_history()
        state.usage_stats.clear()  # Also clear usage statistics
        logger.info(f"Cleared conversation history and usage statistics for user {user_id}")

    async def perform_summarization(self, user_id: int, summarization_text: str):
        """Perform chat summarization: delete old messages and add summarization.

        Args:
            user_id: Telegram user ID
            summarization_text: The summarization content
        """
        if not self.db_manager:
            logger.warning(f"Cannot perform summarization for user {user_id}: no database manager")
            return

        try:
            # Save summarization message to database
            summarization_message = Message(
                id=None,
                user_id=user_id,
                role="assistant",
                content=f"[SUMMARIZATION] {summarization_text}",
                created_at=datetime.now()
            )
            summarization_id = await self.db_manager.save_message(summarization_message)

            # Delete all previous messages except the summarization
            await self.db_manager.delete_summarized_messages(user_id, summarization_id)

            # Update in-memory state
            state = await self.get_user_state(user_id)
            state.conversation_history = [{"role": "assistant", "content": summarization_text}]

            logger.info(f"Performed summarization for user {user_id}, kept message {summarization_id}")

        except Exception as e:
            logger.error(f"Failed to perform summarization for user {user_id}: {e}")
            raise
    
    async def cleanup_old_states(self):
        """Clean up inactive user states."""
        cutoff_time = datetime.now() - timedelta(hours=self.cleanup_hours)
        users_to_remove = [
            user_id
            for user_id, state in self._states.items()
            if state.last_activity < cutoff_time
        ]

        for user_id in users_to_remove:
            logger.info(f"Removing inactive state for user {user_id}")
            del self._states[user_id]

        if users_to_remove:
            logger.info(f"Cleaned up {len(users_to_remove)} inactive states")

        # Also cleanup database if available
        if self.db_manager:
            await self.db_manager.cleanup_old_states(self.cleanup_hours)

    async def get_stats(self) -> Dict:
        """Get statistics about current states.

        Returns:
            Dictionary with statistics
        """
        stats = {
            "total_users": len(self._states)
        }

        if self.db_manager:
            try:
                active_users = await self.db_manager.get_active_users_count()
                stats["active_db_users"] = active_users
            except Exception as e:
                logger.error(f"Failed to get database stats: {e}")

        return stats

    async def get_usage_stats(self) -> Dict[str, float]:
        """Get aggregated usage statistics across all users from database.

        Returns:
            Dictionary with total input_tokens, output_tokens, cost, and requests_count
        """
        if self.db_manager:
            try:
                # Get stats for all users from database
                total_input = 0
                total_output = 0
                total_cost = 0.0
                total_requests = 0
                total_summarization = 0
                total_summarization_input = 0
                total_summarization_output = 0
                total_summarization_cost = 0.0

                # Get all user IDs and aggregate their stats
                # Note: This is a simplified approach - in production you'd want a more efficient query
                for user_id in self._states.keys():
                    try:
                        user_stats = await self.db_manager.get_usage_stats(user_id)
                        total_input += user_stats.chat_input_tokens
                        total_output += user_stats.chat_output_tokens
                        total_cost += user_stats.chat_cost
                        total_requests += user_stats.requests_count
                        total_summarization += user_stats.summarization_count
                        total_summarization_input += user_stats.summarization_input_tokens
                        total_summarization_output += user_stats.summarization_output_tokens
                        total_summarization_cost += user_stats.summarization_cost
                    except Exception as e:
                        logger.error(f"Failed to get stats for user {user_id}: {e}")

                # Calculate combined totals across all users
                total_all_input = total_input + total_summarization_input
                total_all_output = total_output + total_summarization_output
                total_all_cost = total_cost + total_summarization_cost
                total_all_requests = total_requests + total_summarization

                return {
                    "input_tokens": total_input,
                    "output_tokens": total_output,
                    "cost": total_cost,
                    "total_requests": total_requests,
                    "summarization_count": total_summarization,
                    "summarization_input_tokens": total_summarization_input,
                    "summarization_output_tokens": total_summarization_output,
                    "summarization_cost": total_summarization_cost,
                    # Combined totals
                    "total_input_tokens": total_all_input,
                    "total_output_tokens": total_all_output,
                    "total_cost": total_all_cost,
                    "total_requests": total_all_requests,
                    "active_users": len(self._states)
                }
            except Exception as e:
                logger.error(f"Failed to get aggregated usage stats from database: {e}")

        # Fallback to in-memory calculation
        total_input = 0
        total_output = 0
        total_cost = 0.0
        total_requests = 0
        total_summarization = 0
        total_summarization_input = 0
        total_summarization_output = 0
        total_summarization_cost = 0.0

        for state in self._states.values():
            stats = await state.get_usage_stats()
            total_input += stats["input_tokens"]
            total_output += stats["output_tokens"]
            total_cost += stats["cost"]
            total_requests += stats["requests_count"]
            total_summarization += stats["summarization_count"]
            total_summarization_input += stats["summarization_input_tokens"]
            total_summarization_output += stats["summarization_output_tokens"]
            total_summarization_cost += stats["summarization_cost"]

        # Calculate combined totals across all users
        total_all_input = total_input + total_summarization_input
        total_all_output = total_output + total_summarization_output
        total_all_cost = total_cost + total_summarization_cost
        total_all_requests = total_requests + total_summarization

        return {
            "input_tokens": total_input,
            "output_tokens": total_output,
            "cost": total_cost,
            "total_requests": total_requests,
            "summarization_count": total_summarization,
            "summarization_input_tokens": total_summarization_input,
            "summarization_output_tokens": total_summarization_output,
            "summarization_cost": total_summarization_cost,
            # Combined totals
            "total_input_tokens": total_all_input,
            "total_output_tokens": total_all_output,
            "total_cost": total_all_cost,
            "total_requests": total_all_requests,
            "active_users": len(self._states)
        }

