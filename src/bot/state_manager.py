"""User state management for conversation context."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List
from ..llm.modes import RickMode
from ..llm.models import ModelName
from ..config import get_logger

logger = get_logger(__name__)


@dataclass
class UsageStats:
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
    model: ModelName = ModelName.GPT_4_O_MINI
    last_activity: datetime = field(default_factory=datetime.now)
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    usage_stats: List[UsageStats] = field(default_factory=list)
    summarization_enabled: bool = True
    summarization_stats: List[UsageStats] = field(default_factory=list)
    
    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.now()

    def add_message(self, role: str, content: str):
        """Add message to conversation history.

        Args:
            role: Message role ('user' or 'assistant')
            content: Message content
        """
        self.conversation_history.append({"role": role, "content": content})

    def clear_history(self):
        """Clear conversation history and usage statistics."""
        self.conversation_history.clear()
        self.usage_stats.clear()
        self.summarization_stats.clear()

    def add_usage_stats(self, input_tokens: int, output_tokens: int, cost: float):
        """Add usage statistics for a request.

        Args:
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens used
            cost: Cost of the request
        """
        self.usage_stats.append(UsageStats(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost
        ))

    def add_summarization_stats(self, input_tokens: int, output_tokens: int, cost: float):
        """Add usage statistics for a summarization request.

        Args:
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens used
            cost: Cost of the summarization request
        """
        self.summarization_stats.append(UsageStats(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost
        ))

    def get_usage_stats(self) -> Dict[str, float]:
        """Get aggregated usage statistics for this user.

        Returns:
            Dictionary with total input_tokens, output_tokens, and cost
        """
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
    
    def __init__(self, cleanup_hours: int = 24):
        """Initialize state manager.
        
        Args:
            cleanup_hours: Hours of inactivity before state cleanup
        """
        self._states: Dict[int, UserState] = {}
        self.cleanup_hours = cleanup_hours
        logger.info(f"StateManager initialized (cleanup={cleanup_hours}h)")
    
    def get_user_state(self, user_id: int) -> UserState:
        """Get or create user state.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            User state object
        """
        if user_id not in self._states:
            logger.info(f"Creating new state for user {user_id}")
            self._states[user_id] = UserState(user_id=user_id)
        
        state = self._states[user_id]
        state.update_activity()
        return state
    
    def get_user_temperature(self, user_id: int) -> float:
        """Get current temperature setting for user.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Current temperature value (default: 0.3)
        """
        state = self.get_user_state(user_id)
        return state.temperature

    def get_user_model(self, user_id: int) -> ModelName:
        """Get current model for user."""
        state = self.get_user_state(user_id)
        return state.model

    def set_user_model(self, user_id: int, model: ModelName):
        """Set model for user."""
        state = self.get_user_state(user_id)
        old_model = state.model
        state.model = model
        # Clear history when changing model
        state.clear_history()
        logger.info(f"User {user_id} model changed: {old_model} -> {model} (history cleared)")
    
    def set_user_temperature(self, user_id: int, temperature: float):
        """Set temperature for user.

        Args:
            user_id: Telegram user ID
            temperature: Temperature value (0.0-2.0)
        """
        if not (0.0 <= temperature <= 2.0):
            raise ValueError("Temperature must be between 0.0 and 2.0")

        state = self.get_user_state(user_id)
        old_temperature = state.temperature
        state.temperature = temperature
        logger.info(f"User {user_id} temperature changed: {old_temperature} -> {temperature}")

    def get_user_summarization_enabled(self, user_id: int) -> bool:
        """Get summarization setting for user.

        Args:
            user_id: Telegram user ID

        Returns:
            True if summarization is enabled, False otherwise
        """
        state = self.get_user_state(user_id)
        return state.summarization_enabled

    def set_user_summarization_enabled(self, user_id: int, enabled: bool):
        """Set summarization setting for user.

        Args:
            user_id: Telegram user ID
            enabled: Whether to enable summarization
        """
        state = self.get_user_state(user_id)
        old_enabled = state.summarization_enabled
        state.summarization_enabled = enabled
        logger.info(f"User {user_id} summarization changed: {old_enabled} -> {enabled}")
    
    def reset_user_state(self, user_id: int):
        """Reset state for user.

        Args:
            user_id: Telegram user ID
        """
        if user_id in self._states:
            logger.info(f"Resetting state for user {user_id}")
            self._states[user_id] = UserState(user_id=user_id)
        else:
            logger.debug(f"No state to reset for user {user_id}")

    def clear_user_history(self, user_id: int):
        """Clear conversation history for user.

        Args:
            user_id: Telegram user ID
        """
        state = self.get_user_state(user_id)
        state.clear_history()
        state.usage_stats.clear()  # Also clear usage statistics
        logger.info(f"Cleared conversation history and usage statistics for user {user_id}")
    
    def cleanup_old_states(self):
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
    
    def get_stats(self) -> Dict:
        """Get statistics about current states.

        Returns:
            Dictionary with statistics
        """
        return {
            "total_users": len(self._states)
        }

    def get_usage_stats(self) -> Dict[str, float]:
        """Get aggregated usage statistics across all users.

        Returns:
            Dictionary with total input_tokens, output_tokens, cost, and requests_count
        """
        total_input = 0
        total_output = 0
        total_cost = 0.0
        total_requests = 0
        total_summarization = 0
        total_summarization_input = 0
        total_summarization_output = 0
        total_summarization_cost = 0.0

        for state in self._states.values():
            stats = state.get_usage_stats()
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

