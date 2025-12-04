"""User state management for conversation context."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List
from ..config import get_logger

logger = get_logger(__name__)

# Maximum number of messages in history (10 pairs of user-assistant)
MAX_HISTORY_MESSAGES = 20


@dataclass
class UserState:
    """State for individual user conversation."""
    
    user_id: int
    last_activity: datetime = field(default_factory=datetime.now)
    message_history: List[Dict[str, str]] = field(default_factory=list)
    
    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.now()
    
    def add_message(self, role: str, text: str):
        """Add message to history.
        
        Args:
            role: Message role ('user' or 'assistant')
            text: Message text
        """
        self.message_history.append({"role": role, "text": text})
        
        # Remove oldest messages if limit exceeded
        if len(self.message_history) > MAX_HISTORY_MESSAGES:
            # Remove oldest pair (user + assistant) = 2 messages
            messages_to_remove = len(self.message_history) - MAX_HISTORY_MESSAGES
            self.message_history = self.message_history[messages_to_remove:]
            logger.debug(f"Trimmed history for user {self.user_id}: removed {messages_to_remove} oldest messages")
    
    def clear_history(self):
        """Clear message history."""
        self.message_history.clear()
        logger.info(f"Cleared history for user {self.user_id}")
    
    def get_history(self) -> List[Dict[str, str]]:
        """Get conversation history.
        
        Returns:
            List of message dictionaries with 'role' and 'text' keys
        """
        return self.message_history.copy()


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
    
    def clear_user_history(self, user_id: int):
        """Clear message history for specific user.
        
        Args:
            user_id: Telegram user ID
        """
        if user_id in self._states:
            self._states[user_id].clear_history()
            logger.info(f"Cleared history for user {user_id}")
    
    def get_stats(self) -> Dict:
        """Get statistics about current states.
        
        Returns:
            Dictionary with statistics
        """
        total_messages = sum(len(state.message_history) for state in self._states.values())
        return {
            "total_users": len(self._states),
            "total_messages_in_history": total_messages
        }

