from typing import Dict, List, Optional, AsyncIterator
import logging
from langgraph.graph import Graph
from pydantic import BaseModel
from langchain_core.language_models import BaseChatModel

from .interfaces import BaseEnvironment, EnvironmentType, SharedContext
from .types import (
    create_default_agent_state,  # Add this import
)
from graph.nodes import create_agent_graph, EnvironmentOutput

logger = logging.getLogger(__name__)


class EnvironmentDelegator:
    """Routes actions to appropriate environments and manages transitions"""

    def __init__(self, llm: Optional[BaseChatModel] = None):
        self.environments: Dict[EnvironmentType, BaseEnvironment] = {}
        self.llm = llm
        self._graph = None  # Initialize private graph variable

        logger.info("Creating agent graph...")
        try:
            self._graph = create_agent_graph()
            if not self._graph:
                raise RuntimeError("Graph creation returned None")
            logger.info(f"Graph created successfully: {type(self._graph)}")
        except Exception as e:
            logger.error(f"Failed to create agent graph: {str(e)}", exc_info=True)
            raise

        self.shared_context = SharedContext(
            task_description="",
            current_environment=EnvironmentType.BROWSER,
            agent_state=create_default_agent_state(),  # Use imported function
        )

    @property
    def graph(self) -> Optional[Graph]:
        """Protect graph access and ensure it exists"""
        if not self._graph:
            logger.error("Attempted to access uninitialized graph")
        return self._graph

    def register_environment(
        self, env_type: EnvironmentType, environment: BaseEnvironment
    ) -> None:
        """Register a new environment"""
        self.environments[env_type] = environment
        logger.info(f"Registered environment: {env_type}")

    async def initialize_environments(self) -> None:
        """Initialize all registered environments"""
        for env in self.environments.values():
            await env.initialize(self.shared_context)

    def determine_environment(self, action: Dict) -> Optional[EnvironmentType]:
        """Determine which environment should handle an action"""
        for env_type, environment in self.environments.items():
            if environment.can_handle_action(action):
                return env_type
        return None

    async def execute_action(self, action: Dict) -> dict:
        """Execute an action in the appropriate environment"""
        logger.info("Starting execute_action")
        logger.debug(f"Graph state: {self._graph is not None}")
        logger.debug(f"Action: {action}")

        if not self._graph:
            logger.error("Graph is None in execute_action")
            raise RuntimeError("Graph not initialized")

        env_type = self.determine_environment(action)
        if not env_type or env_type not in self.environments:
            raise ValueError(f"No environment can handle action: {action}")

        environment = self.environments[env_type]
        self.shared_context.current_environment = env_type

        try:
            output: EnvironmentOutput = await environment.execute(action)
            self.shared_context.agent_state["environment_output"] = output.dict()

            # Pass both llm and env_registry in config
            config = {
                "configurable": {"llm": self.llm, "env_registry": self.environments}
            }

            logger.debug(f"Executing graph with config: {config}")
            result = await self._graph.ainvoke(
                self.shared_context.agent_state, config=config
            )

            logger.info("Graph invocation successful")
            self.shared_context.agent_state.update(result)
            return output.dict()

        except Exception as e:
            logger.error(f"Action execution failed: {str(e)}", exc_info=True)
            raise

    async def cleanup(self) -> None:
        """Clean up all environments"""
        for environment in self.environments.values():
            await environment.cleanup()
