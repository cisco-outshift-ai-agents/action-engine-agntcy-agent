from abc import ABC
from typing import Any, Dict, Optional

from pydantic import BaseModel

from core.interfaces import BaseEnvironment, BaseEnvironmentState, SharedContext


class EnvironmentStateBase(BaseEnvironmentState):
    """Base state model with common fields across environments"""

    is_ready: bool = False
    is_busy: bool = False
    last_action: Optional[Dict[str, Any]] = None
    last_error: Optional[str] = None


class EnvironmentBase(BaseEnvironment, ABC):
    """Base implementation with common functionality for environments"""

    def __init__(self):
        self.state = EnvironmentStateBase(status="initialized")
        self.shared_context: Optional[SharedContext] = None

    async def initialize(self, context: SharedContext) -> None:
        """Initialize with shared context"""
        self.shared_context = context
        self.state.is_ready = True

    async def get_state(self) -> BaseEnvironmentState:
        """Get current environment state"""
        return self.state

    def _update_state(self, **kwargs) -> None:
        """Update state with new values"""
        for key, value in kwargs.items():
            if hasattr(self.state, key):
                setattr(self.state, key, value)
