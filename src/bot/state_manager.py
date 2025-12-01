"""User state management for conversation context."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from ..llm.modes import RickMode
from ..config import get_logger

logger = get_logger(__name__)


@dataclass
class UserState:
    """State for individual user conversation."""
    
    user_id: int
    current_mode: RickMode = RickMode.NORMAL
    dialog_history: List[Dict[str, str]] = field(default_factory=list)
    last_activity: datetime = field(default_factory=datetime.now)
    message_count: int = 0
    
    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.now()
        self.message_count += 1
    
    def add_message(self, role: str, text: str):
        """Add message to dialog history.
        
        Args:
            role: Message role (user/assistant)
            text: Message text
        """
        self.dialog_history.append({
            "role": role,
            "text": text
        })
    
    def clear_history(self):
        """Clear dialog history."""
        self.dialog_history.clear()
        logger.info(f"Cleared history for user {self.user_id}")
    
    def get_history(self, max_length: Optional[int] = None) -> List[Dict[str, str]]:
        """Get dialog history with optional limit.
        
        Args:
            max_length: Maximum number of messages to return
            
        Returns:
            List of message dictionaries
        """
        if max_length and len(self.dialog_history) > max_length:
            return self.dialog_history[-max_length:]
        return self.dialog_history


class StateManager:
    """Manager for user conversation states."""
    
    def __init__(self, max_history_length: int = 10, cleanup_hours: int = 24):
        """Initialize state manager.
        
        Args:
            max_history_length: Maximum messages to keep in history
            cleanup_hours: Hours of inactivity before state cleanup
        """
        self._states: Dict[int, UserState] = {}
        self.max_history_length = max_history_length
        self.cleanup_hours = cleanup_hours
        logger.info(f"StateManager initialized (max_history={max_history_length}, cleanup={cleanup_hours}h)")
    
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
    
    def get_user_mode(self, user_id: int) -> RickMode:
        """Get current conversation mode for user.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Current Rick mode
        """
        state = self.get_user_state(user_id)
        return state.current_mode
    
    def set_user_mode(self, user_id: int, mode: RickMode):
        """Set conversation mode for user.
        
        Args:
            user_id: Telegram user ID
            mode: New Rick mode
        """
        state = self.get_user_state(user_id)
        old_mode = state.current_mode
        state.current_mode = mode
        logger.info(f"User {user_id} mode changed: {old_mode.value} -> {mode.value}")
    
    def add_user_message(self, user_id: int, text: str):
        """Add user message to history.
        
        Args:
            user_id: Telegram user ID
            text: Message text
        """
        state = self.get_user_state(user_id)
        state.add_message("user", text)
        
        # Trim history if too long
        if len(state.dialog_history) > self.max_history_length * 2:
            state.dialog_history = state.dialog_history[-self.max_history_length:]
            logger.debug(f"Trimmed history for user {user_id}")
    
    def add_assistant_message(self, user_id: int, text: str):
        """Add assistant message to history.
        
        Args:
            user_id: Telegram user ID
            text: Message text
        """
        state = self.get_user_state(user_id)
        state.add_message("assistant", text)
    
    def get_conversation_history(
        self,
        user_id: int,
        max_length: Optional[int] = None
    ) -> List[Dict[str, str]]:
        """Get conversation history for user.
        
        Args:
            user_id: Telegram user ID
            max_length: Maximum messages to return
            
        Returns:
            List of message dictionaries
        """
        state = self.get_user_state(user_id)
        return state.get_history(max_length or self.max_history_length)
    
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
            "total_users": len(self._states),
            "active_conversations": sum(
                1 for state in self._states.values()
                if state.dialog_history
            ),
            "total_messages": sum(
                state.message_count for state in self._states.values()
            )
        }

