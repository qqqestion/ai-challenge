"""User state management for conversation context."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict
from ..llm.modes import RickMode
from ..llm.models import ModelName
from ..config import get_logger

logger = get_logger(__name__)


@dataclass
class UserState:
    """State for individual user conversation."""
    
    user_id: int
    current_mode: RickMode = RickMode.NORMAL
    temperature: float = 0.3
    model: ModelName = ModelName.GPT_4_O_MINI
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
        logger.info(f"User {user_id} model changed: {old_model} -> {model}")
    
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
            "total_users": len(self._states)
        }

