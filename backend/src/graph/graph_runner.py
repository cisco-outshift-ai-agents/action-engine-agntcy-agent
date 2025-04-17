import json
import logging
import os
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, Optional
from langgraph.types import Command, interrupt
from uuid import uuid4

from pydantic import BaseModel

from src.graph.environments.browser import BrowserSession
from src.graph.environments.planning import PlanningEnvironment
from src.graph.environments.terminal import TerminalManager
from src.graph.global_configurable import context
from src.graph.graph import action_engine_graph
from src.graph.types import GraphConfig, create_default_agent_state
from src.utils.agent_state import AgentState
from src.utils.utils import get_llm_model

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    provider: str
    model_name: str
    temperature: float
    base_url: str
    api_key: str


@dataclass
class AgentConfig:
    use_own_browser: bool
    keep_browser_open: bool
    headless: bool
    disable_security: bool
    window_w: int
    window_h: int
    task: str
    add_infos: str
    max_steps: int
    use_vision: bool
    max_actions_per_step: int
    tool_calling_method: str
    limit_num_image_per_llm_call: Optional[int]


class GraphRunner:
    """Manages execution of the LangGraph agent system while maintaining global resources"""

    def __init__(self, terminal_manager: TerminalManager):
        self.llm = None
        self.browser_session = BrowserSession()
        self.terminal_manager = terminal_manager or TerminalManager()
        self.planning_env = PlanningEnvironment()
        self.graph = None
        self.thread_id = None
        self.current_config = None
        self.current_state = None  # Store the current state
        self.agent_state = AgentState()

    async def initialize(self, agent_config: AgentConfig) -> None:
        """Initialize global resources and LLM"""
        logger.debug("Initializing GraphRunner with agent config")

        # Initialize LLM and store in both places
        self.llm = get_llm_model(
            provider=os.getenv("LLM_PROVIDER", "openai"),
            model_name=os.getenv("LLM_MODEL_NAME", "gpt-4o"),
            temperature=float(os.getenv("LLM_TEMPERATURE", 1.0)),
            llm_base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
            llm_api_key=os.getenv("LLM_API_KEY", ""),
        )
        context.llm = self.llm

        # Initialize graph
        self.graph = action_engine_graph

        # Initialize browser session
        await self.browser_session.initialize(
            window_w=agent_config.window_w,
            window_h=agent_config.window_h,
        )

        # Store resources in context
        context.browser = self.browser_session.browser
        context.browser_context = self.browser_session.browser_context
        context.dom_service = self.browser_session.dom_service
        context.terminal_manager = self.terminal_manager
        context.planning_environment = self.planning_env

    async def execute(
        self, task: str, thread_id: Optional[str] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """Execute task using LangGraph with proper streaming"""
        try:
            logger.info("Starting graph execution with streaming")

            thread_id = thread_id or str(uuid4())
            self.thread_id = thread_id

            if not self.llm:
                raise RuntimeError("LLM not initialized")

            agent_state = create_default_agent_state(task)
            config: GraphConfig = {
                "configurable": {
                    "llm": self.llm,
                    "browser": context.browser,
                    "browser_context": context.browser_context,
                    "dom_service": context.dom_service,
                    "terminal_manager": context.terminal_manager,
                    "planning_environment": context.planning_environment,
                    "thread_id": thread_id,
                }
            }

            self.current_config = config
            self.current_state = agent_state

            # Use astream and await the async generator
            try:
                async for step_output in self.graph.astream(agent_state, config):
                    logger.info(f"Step output: {step_output}")

                    # # Check for stop request after each step
                    if self.agent_state.is_stop_requested():
                        logger.info("Stop requested, terminating execution")
                        # Set exiting flag to ensure graph doesn't continue
                        self.current_state["exiting"] = True
                        break

                    # Handle the interrupt
                    if isinstance(step_output, dict) and "__interrupt__" in step_output:
                        logger.info("Found interrupt in step_output")

                        interrupt_data = None

                        interrupt_obj = step_output["__interrupt__"]
                        if isinstance(interrupt_obj, tuple) and len(interrupt_obj) > 0:
                            interrupt_obj = interrupt_obj[0]

                        # Get the actual message data from the interrupt
                        if hasattr(interrupt_obj, "message"):
                            interrupt_data = interrupt_obj.message
                        elif hasattr(interrupt_obj, "value"):
                            interrupt_data = interrupt_obj.value
                        else:
                            # Fallback - use the object itself if it's a dict
                            interrupt_data = (
                                interrupt_obj if isinstance(interrupt_obj, dict) else {}
                            )
                        approval_request = {
                            "type": "approval_request",
                            "data": interrupt_data,
                            "thread_id": thread_id,
                        }

                        formatted_interrupt_data = serialize_graph_response(
                            approval_request
                        )
                        yield formatted_interrupt_data
                        return

                    # Store the last completed node's output to keep state
                    if isinstance(step_output, dict) and len(step_output) == 1:
                        node_name = list(step_output.keys())[0]
                        if node_name != "__interrupt__":
                            logger.info(
                                f"Updating current state from node: {node_name}"
                            )
                            self.current_state = step_output[node_name]

                    # Normal step output
                    formatted_output = serialize_graph_response(step_output)
                    if isinstance(formatted_output, dict):
                        formatted_output["thread_id"] = thread_id

                    yield formatted_output

            except Exception as e:
                logger.error(f"Error in graph execution: {str(e)}", exc_info=True)
                yield {"error": str(e), "thread_id": thread_id}

        except Exception as e:
            logger.error(f"Outer graph execution error: {str(e)}", exc_info=True)
            yield {"error": str(e), "thread_id": thread_id}

    async def handle_approval(
        self, approval: Dict[str, Any]
    ) -> AsyncIterator[Dict[str, Any]]:
        """Handle approval response from the user"""
        try:
            if not self.graph:
                raise ValueError("Graph not initialized")

            approved = approval.get("approved", False)
            logger.info(f"Handling approval: {approved}")

            tool_call = approval.get("tool_call", {})

            self.current_state["pending_approval"] = {
                "tool_call": tool_call,
                "approved": approved,
            }

            if not approved:
                logger.info("Tool call not approved, terminating")
                self.current_state["thought"] = "User declined to execute command"

                if "messages" in self.current_state:
                    decline_message = {
                        "type": "HumanMessage",
                        "content": f"I don't want to run the command: '{tool_call.get('args', {}).get('script', '')}'.",
                    }
                    self.current_state["messages"].append(decline_message)

            command = Command(resume=self.current_state)

            # Update the config with required checkpoint values and add the required checkpoint values

            config_with_checkpoint = dict(self.current_config)
            if "configurable" not in config_with_checkpoint:
                config_with_checkpoint["configurable"] = {}

            config_with_checkpoint["configurable"]["thread_id"] = self.thread_id

            logger.info(f"Current state after approval: {self.current_state}")

            # Continue graph execution with the approval response
            async for step_output in self.graph.astream(
                command, config_with_checkpoint
            ):
                logger.info(f"Post-approval step output: {step_output}")

                if isinstance(step_output, dict) and len(step_output) == 1:
                    node_name = list(step_output.keys())[0]
                    if node_name != "__interrupt__":
                        self.current_state = step_output[node_name]

                # Handle interrupts
                if isinstance(step_output, dict) and "__interrupt__" in step_output:
                    logger.info("Found interrupt in post-approval step_output")
                    interrupt_data = None
                    interrupt_obj = step_output["__interrupt__"]
                    if isinstance(interrupt_obj, tuple) and len(interrupt_obj) > 0:
                        interrupt_obj = interrupt_obj[0]

                    if hasattr(interrupt_obj, "message"):
                        interrupt_data = interrupt_obj.message
                    elif hasattr(interrupt_obj, "value"):
                        interrupt_data = interrupt_obj.value
                    else:
                        interrupt_data = (
                            interrupt_obj if isinstance(interrupt_obj, dict) else {}
                        )

                    approval_request = {
                        "type": "approval_request",
                        "data": interrupt_data,
                        "thread_id": self.thread_id,
                    }
                    safe_interrupt_data = serialize_graph_response(approval_request)
                    yield safe_interrupt_data
                    return

                # Normal step output
                formatted_output = serialize_graph_response(step_output)
                if isinstance(formatted_output, dict):
                    formatted_output["thread_id"] = self.thread_id
                yield formatted_output

        except Exception as e:
            logger.error(f"Error handling approval: {str(e)}", exc_info=True)
            yield {"error": str(e), "thread_id": self.thread_id}

    async def stop_agent(self) -> dict:
        """Stop the agent execution"""
        try:
            logger.info("Stop agent called - terminating execution")

            if self.current_state:
                self.current_state["exiting"] = True
                self.current_state["thought"] = "User requested to stop execution"
                self.current_state["pending_approval"] = {}
                self.current_state["tool_calls"] = []
                logger.info("Set exiting flag in current_state")

            # Signal stop through the AgentState singleton
            self.agent_state.request_stop()
            logger.info("Stop requested through agent state")
            await self.cleanup()

            stop_response = {
                "summary": "Stopped",
                "stopped": True,
            }
            return stop_response
        except Exception as e:
            error_msg = f"Error during stop: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}

    async def cleanup(self) -> None:
        """Cleanup global resources"""
        await self.browser_session.cleanup()
        await self.terminal_manager.delete_terminal()

        # Clear context
        context.browser = None
        context.browser_context = None
        context.dom_service = None
        context.terminal_manager = None
        context.planning_environment = None


def serialize_graph_response(data: Any) -> Any:
    """Convert any object to a JSON-serializable format"""

    # Handle BaseModel instances
    if isinstance(data, BaseModel):
        return data.model_dump()

    # Handle dictionaries
    elif isinstance(data, dict):
        return {
            key: serialize_graph_response(value)
            for key, value in data.items()
            if key != "__interrupt__"
        }

    elif isinstance(data, list):
        return [serialize_graph_response(item) for item in data]

    elif isinstance(data, tuple):
        return [serialize_graph_response(item) for item in data]

    elif isinstance(data, set):
        return [serialize_graph_response(item) for item in data]

    try:
        json.dumps(data)
        return data
    except (TypeError, OverflowError):
        return str(data)
