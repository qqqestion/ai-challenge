"""User state management for conversation context."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict
from ..config import get_logger

logger = get_logger(__name__)


@dataclass
class UserState:
    """State for individual user conversation."""
    
    user_id: int
    last_activity: datetime = field(default_factory=datetime.now)
    
    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.now()


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
    
    def get_stats(self) -> Dict:
        """Get statistics about current states.
        
        Returns:
            Dictionary with statistics
        """
        return {
            "total_users": len(self._states)
        }

