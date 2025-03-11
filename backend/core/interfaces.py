from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from langgraph.graph import Graph

from .types import EnvironmentType, EnvironmentOutput, AgentState


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
    """Base environment interface that all environments must implement"""

    @abstractmethod
    async def initialize(self, context: SharedContext) -> None:
        """Initialize the environment"""
        pass

    @abstractmethod
    async def execute(self, action: Dict[str, Any]) -> EnvironmentOutput:
        """Execute an action in this environment and return graph-compatible output"""
        pass

    @abstractmethod
    async def get_state(self) -> BaseEnvironmentState:
        """Get the current state of this environment"""
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up any resources used by this environment"""
        pass

    @abstractmethod
    def can_handle_action(self, action: Dict[str, Any]) -> bool:
        """Determine if this environment can handle the given action"""
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
