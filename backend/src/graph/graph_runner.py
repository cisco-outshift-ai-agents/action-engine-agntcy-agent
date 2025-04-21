"""Graph-based execution engine with thread-aware environment management."""

import json
import logging
import os
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, Optional
from langgraph.types import Command
from uuid import uuid4

from pydantic import BaseModel

from src.graph.environments.manager import environment_manager
from src.graph.global_configurable import context
from src.graph.graph import action_engine_graph
from src.graph.types import GraphConfig, create_default_agent_state
from src.utils.agent_state import AgentState
from src.utils.utils import get_llm_model

logger = logging.getLogger(__name__)


@dataclass
class EnvironmentConfig:
    """Configuration for thread environments."""

    # LLM Settings
    llm_provider: str = "openai"
    llm_model: str = "gpt-4"
    llm_temperature: float = 0.7
    llm_base_url: Optional[str] = None
    llm_api_key: Optional[str] = None

    # Browser settings
    use_browser: bool = True
    use_own_browser: bool = False
    keep_browser_open: bool = True
    headless: bool = True
    window_w: int = 1280
    window_h: int = 720
    disable_security: bool = False

    # Terminal settings
    use_terminal: bool = True

    # Task settings
    task: str = ""
    max_steps: int = 10
    max_actions_per_step: int = 5
    tool_calling_method: str = "default_method"


class GraphRunner:
    """Manages execution of the LangGraph agent system with thread-aware environments."""

    def __init__(self):
        self.llm = None
        self.graph = None
        self._thread_configs: Dict[str, EnvironmentConfig] = {}
        self._thread_states: Dict[str, Dict[str, Any]] = {}

    def _parse_config(
        self, config: Optional[Dict[str, Any]] = None
    ) -> EnvironmentConfig:
        """Parse raw config dict into EnvironmentConfig."""
        config_dict = {
            # Default LLM settings from env
            "llm_provider": os.getenv("LLM_PROVIDER", "openai"),
            "llm_model": os.getenv("LLM_MODEL_NAME", "gpt-4"),
            "llm_temperature": float(os.getenv("LLM_TEMPERATURE", 0.7)),
            "llm_base_url": os.getenv("LLM_BASE_URL"),
            "llm_api_key": os.getenv("LLM_API_KEY"),
        }

        # Update with provided config
        if config:
            config_dict.update(config)

        return EnvironmentConfig(
            **{
                k: config_dict.get(k, getattr(EnvironmentConfig, k))
                for k in EnvironmentConfig.__annotations__
            }
        )

    async def initialize_llm(self, config: EnvironmentConfig):
        """Initialize LLM with config."""
        self.llm = get_llm_model(
            provider=config.llm_provider,
            model_name=config.llm_model,
            temperature=config.llm_temperature,
            llm_base_url=config.llm_base_url,
            llm_api_key=config.llm_api_key,
        )
        context.llm = self.llm

        if self.graph is None:
            self.graph = action_engine_graph

    async def execute(
        self,
        task: str,
        thread_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """Execute task using LangGraph with thread-aware environments."""
        try:
            thread_id = thread_id or str(uuid4())
            logger.info(f"Starting execution for thread {thread_id}")

            # Parse and store thread config
            config_dict = config or {}
            config_dict["task"] = task
            thread_config = self._parse_config(config_dict)
            self._thread_configs[thread_id] = thread_config

            # Initialize LLM with thread config
            await self.initialize_llm(thread_config)

            # Get thread environments
            envs = await environment_manager.get_or_create(thread_id)

            # Initialize environments with config
            await envs.initialize(
                {
                    "window_w": thread_config.window_w,
                    "window_h": thread_config.window_h,
                    "headless": thread_config.headless,
                    "use_own_browser": thread_config.use_own_browser,
                    "keep_browser_open": thread_config.keep_browser_open,
                    "disable_security": thread_config.disable_security,
                }
            )

            # Create agent state
            agent_state = create_default_agent_state(task)
            agent_state.update(
                {
                    "max_steps": thread_config.max_steps,
                    "max_actions_per_step": thread_config.max_actions_per_step,
                    "tool_calling_method": thread_config.tool_calling_method,
                }
            )

            # Create graph config with thread-specific environments
            graph_config: GraphConfig = {
                "configurable": {
                    "llm": self.llm,
                    "browser": envs.browser_manager.browser,
                    "browser_context": envs.browser_manager.browser_context,
                    "dom_service": envs.browser_manager.dom_service,
                    "terminal_manager": envs.terminal_manager,
                    "planning_environment": envs.planning_manager,
                    "thread_id": thread_id,
                }
            }

            # Store thread state
            self._thread_states[thread_id] = {
                "agent_state": agent_state,
                "config": graph_config,
            }

            try:
                async for step_output in self.graph.astream(agent_state, graph_config):
                    logger.info(f"Step output for thread {thread_id}")

                    if isinstance(step_output, dict) and "__interrupt__" in step_output:
                        formatted_interrupt = handle_interrupt(step_output, thread_id)
                        yield formatted_interrupt
                        return

                    if isinstance(step_output, dict) and len(step_output) == 1:
                        node_name = list(step_output.keys())[0]
                        if node_name != "__interrupt__":
                            self._thread_states[thread_id]["agent_state"] = step_output[
                                node_name
                            ]

                    formatted_output = serialize_graph_response(step_output)
                    if isinstance(formatted_output, dict):
                        formatted_output["thread_id"] = thread_id
                    yield formatted_output

            except Exception as e:
                logger.error(f"Error in graph execution: {str(e)}")
                yield {"error": str(e), "thread_id": thread_id}

        except Exception as e:
            logger.error(f"Error in execute: {str(e)}")
            yield {"error": str(e), "thread_id": thread_id}

        finally:
            # Cleanup if not keeping browser open
            thread_config = self._thread_configs.get(thread_id)
            if thread_config and not thread_config.keep_browser_open:
                await self.cleanup(thread_id)

    async def handle_interrupt(
        self, thread_id: str, data: Dict[str, Any]
    ) -> AsyncIterator[Dict[str, Any]]:
        """Handle interrupt with thread state."""
        try:
            if thread_id not in self._thread_states:
                raise ValueError(f"No state found for thread {thread_id}")

            thread_state = self._thread_states[thread_id]
            agent_state = thread_state["agent_state"]
            graph_config = thread_state["config"]

            # Update state with interrupt response
            agent_state["pending_approval"] = data
            command = Command(resume=agent_state)

            async for step_output in self.graph.astream(command, graph_config):
                if isinstance(step_output, dict) and "__interrupt__" in step_output:
                    formatted_interrupt = handle_interrupt(step_output, thread_id)
                    yield formatted_interrupt
                    return

                if isinstance(step_output, dict) and len(step_output) == 1:
                    node_name = list(step_output.keys())[0]
                    if node_name != "__interrupt__":
                        thread_state["agent_state"] = step_output[node_name]

                formatted_output = serialize_graph_response(step_output)
                if isinstance(formatted_output, dict):
                    formatted_output["thread_id"] = thread_id
                yield formatted_output

        except Exception as e:
            logger.error(f"Error handling interrupt: {str(e)}")
            yield {"error": str(e), "thread_id": thread_id}

    async def cleanup(self, thread_id: str) -> None:
        """Clean up thread resources."""
        try:
            # Cleanup environments
            await environment_manager.cleanup(thread_id)

            # Clear thread state
            self._thread_states.pop(thread_id, None)
            self._thread_configs.pop(thread_id, None)

        except Exception as e:
            logger.error(f"Error cleaning up thread {thread_id}: {e}")


def serialize_graph_response(data: Any) -> Any:
    """Convert Pydantic models and other types to serializable format."""
    if isinstance(data, BaseModel):
        return data.model_dump()
    elif isinstance(data, dict):
        return {
            key: serialize_graph_response(value)
            for key, value in data.items()
            if key != "__interrupt__"
        }
    elif isinstance(data, (list, tuple, set)):
        return [serialize_graph_response(item) for item in data]

    try:
        json.dumps(data)
        return data
    except (TypeError, OverflowError):
        return str(data)


def handle_interrupt(
    step_output: Dict[str, Any], thread_id: Optional[str] = None
) -> Dict[str, Any]:
    """Process an interrupt and format for consumption."""
    logger.info("Processing interrupt")

    interrupt_data = None
    interrupt_obj = step_output["__interrupt__"]

    if isinstance(interrupt_obj, tuple) and len(interrupt_obj) > 0:
        interrupt_obj = interrupt_obj[0]

    if hasattr(interrupt_obj, "message"):
        interrupt_data = interrupt_obj.message
    elif hasattr(interrupt_obj, "value"):
        interrupt_data = interrupt_obj.value
    else:
        interrupt_data = interrupt_obj if isinstance(interrupt_obj, dict) else {}

    approval_request = {
        "type": "approval_request",
        "data": interrupt_data,
        "thread_id": thread_id,
    }

    return serialize_graph_response(approval_request)
