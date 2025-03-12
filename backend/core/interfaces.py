from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from langgraph.graph import Graph
from pydantic import BaseModel

from .types import AgentState, EnvironmentOutput, EnvironmentType


class SharedContext(BaseModel):
    """Context shared between all environments"""

    task_description: str
    execution_history: List[Dict[str, Any]] = []
    global_memory: Dict[str, Any] = {}
    current_environment: EnvironmentType
    environment_states: Dict[EnvironmentType, Dict[str, Any]] = {}
    agent_state: "AgentState"  # Forward reference

    class Config:
        arbitrary_types_allowed = True


class BaseEnvironmentState(BaseModel):
    """Base state model that all environments must implement"""

    status: str
    error: Optional[str] = None
    metadata: Dict[str, Any] = {}


class BaseEnvironment(ABC):
    """Defines the core interface for environment implementations (browser, terminal, code)

    Each environment provides isolated execution capabilities while maintaining consistent
    state management and error handling patterns. This abstraction ensures that:

    1. All environments share the same initialization lifecycle
    2. State updates flow through a common interface
    3. Resources are properly cleaned up on completion
    """

    @abstractmethod
    async def initialize(self, context: SharedContext) -> None:
        """Set up environment-specific resources and state"""
        pass

    @abstractmethod
    async def execute(self, action: Dict[str, Any]) -> EnvironmentOutput:
        """Run actions while maintaining proper state management"""
        pass

    @abstractmethod
    async def get_state(self) -> BaseEnvironmentState:
        """Get serializable state for environment handoffs"""
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Release environment resources and reset state"""
        pass

    @abstractmethod
    def can_handle_action(self, action: Dict[str, Any]) -> bool:
        """Verify if this environment supports the requested action"""
        pass


class BaseToolRegistry(ABC):
    """Base class for tool registries"""

    @abstractmethod
    def register_tool(self, name: str, tool_func: Any) -> None:
        """Register a new tool"""
        pass

    @abstractmethod
    def get_tool(self, name: str) -> Any:
        """Get a registered tool by name"""
        pass

    @abstractmethod
    def list_tools(self) -> List[str]:
        """List all registered tools"""
        pass
