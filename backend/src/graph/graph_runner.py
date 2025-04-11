import logging
import os
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, Optional
from langgraph.types import Command
from uuid import uuid4

from pydantic import BaseModel

from src.graph.environments.browser import BrowserSession
from src.graph.environments.planning import PlanningEnvironment
from src.graph.environments.terminal import TerminalManager
from src.graph.global_configurable import context
from src.graph.graph import action_engine_graph
from src.graph.types import AgentState, GraphConfig, create_default_agent_state
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

            if not self.llm:
                raise RuntimeError("LLM not initialized")

            self.current_state = create_default_agent_state(task)
            self.current_config = {
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
            thread_id = thread_id or str(uuid4())
            self.thread_id = thread_id
            logger.info(f"Thread ID: {thread_id}")

            # Use astream and properly await the async generator
            try:
                async for step_output in self.graph.astream(
                    self.current_state, self.current_config
                ):
                    logger.info(f"Step output: {step_output}")

                    # Check for an interrupt in the step_output
                    if isinstance(step_output, dict) and "__interrupt__" in step_output:
                        logger.info("Found interrupt in step_output")

                        # Extract interrupt data safely
                        interrupt_obj = step_output["__interrupt__"]

                        # If it's a tuple, the first element should be the Interrupt object
                        if isinstance(interrupt_obj, tuple) and len(interrupt_obj) > 0:
                            interrupt_obj = interrupt_obj[0]

                        # Extract data from interrupt
                        interrupt_data = getattr(interrupt_obj, "value", {})

                        # Format to match regular node output structure
                        # This creates a structure like {"approval_request": {...state...}, "thread_id": "..."}
                        response = {
                            "approval_request": self.current_state,
                            "thread_id": thread_id,
                        }

                        # Add the tool_call and message to the state for UI use
                        if isinstance(interrupt_data, dict):
                            response["approval_request"]["tool_call"] = (
                                interrupt_data.get("tool_call", {})
                            )
                            response["approval_request"]["approval_message"] = (
                                interrupt_data.get("message", "")
                            )

                        logger.info(
                            f"Formatted interrupt response to match node output structure"
                        )
                        yield response
                        return

                    # Store the last completed node's output to keep state
                    if isinstance(step_output, dict) and len(step_output) == 1:
                        node_name = list(step_output.keys())[0]
                        if node_name != "__interrupt__":
                            logger.info(
                                f"Updating current state from node: {node_name}"
                            )
                            self.current_state = step_output[node_name]

                    # Add thread_id to output
                    safe_output = serialize_graph_response(step_output)
                    if isinstance(safe_output, dict):
                        safe_output["thread_id"] = thread_id

                    yield safe_output

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

            # Get the approved flag
            approved = approval.get("approved", False)
            logger.info(f"Handling approval: {approved}")

            # Store the tool call info
            tool_call = approval.get("tool_call", {})

            # Ensure pending_tool_calls exists in the state
            if "pending_tool_calls" not in self.current_state:
                logger.warning("No pending_tool_calls found in state, creating it")
                self.current_state["pending_tool_calls"] = []

                # Extract tool calls from messages if needed
                if "messages" in self.current_state:
                    for message in reversed(self.current_state["messages"]):
                        if (
                            message.get("type") == "AIMessage"
                            and "tool_calls" in message
                        ):
                            terminal_tools = [
                                tc
                                for tc in message.get("tool_calls", [])
                                if tc.get("name") == "terminal"
                            ]
                            if terminal_tools:
                                self.current_state["pending_tool_calls"] = (
                                    terminal_tools
                                )
                                logger.info(
                                    f"Extracted terminal tools from messages: {terminal_tools}"
                                )
                                break

            # Set approval state
            self.current_state["pending_approval"] = {
                "tool_call": tool_call,
                "approved": approved,
            }

            if approved:
                # Add to approved_tool_calls if approved
                if "approved_tool_calls" not in self.current_state:
                    self.current_state["approved_tool_calls"] = []
                self.current_state["approved_tool_calls"].append(tool_call)
                logger.info(f"Added tool call to approved_tool_calls: {tool_call}")

            # Create a command to resume with the current state
            command = Command(resume=self.current_state)

            # Continue graph execution with the approval response
            try:
                async for step_output in self.graph.astream(
                    command, self.current_config
                ):
                    logger.info(f"Post-approval step output: {step_output}")

                    # Check for an interrupt in the step_output
                    if isinstance(step_output, dict) and "__interrupt__" in step_output:
                        logger.info("Found interrupt in post-approval step_output")

                        # Extract interrupt data safely
                        interrupt_obj = step_output["__interrupt__"]

                        # If it's a tuple, the first element should be the Interrupt object
                        if isinstance(interrupt_obj, tuple) and len(interrupt_obj) > 0:
                            interrupt_obj = interrupt_obj[0]

                        # Extract data from interrupt
                        interrupt_data = getattr(interrupt_obj, "value", {})

                        # Format to match regular node output structure
                        # This creates a structure like {"approval_request": {...state...}, "thread_id": "..."}
                        response = {
                            "approval_request": self.current_state,
                            "thread_id": self.thread_id,
                        }

                        # Add the tool_call and message to the state for UI use
                        if isinstance(interrupt_data, dict):
                            response["approval_request"]["tool_call"] = (
                                interrupt_data.get("tool_call", {})
                            )
                            response["approval_request"]["approval_message"] = (
                                interrupt_data.get("message", "")
                            )

                        logger.info(
                            f"Formatted post-approval interrupt response to match node output structure"
                        )
                        yield response
                        return

                    # Store the last completed node's output to keep state
                    if isinstance(step_output, dict) and len(step_output) == 1:
                        node_name = list(step_output.keys())[0]
                        if node_name != "__interrupt__":
                            logger.info(
                                f"Updating current state from node: {node_name}"
                            )
                            self.current_state = step_output[node_name]

                    # Add thread_id to output
                    safe_output = serialize_graph_response(step_output)
                    if isinstance(safe_output, dict):
                        safe_output["thread_id"] = self.thread_id

                    yield safe_output

            except Exception as e:
                logger.error(
                    f"Error in post-approval processing: {str(e)}", exc_info=True
                )
                yield {"error": str(e), "thread_id": self.thread_id}

        except Exception as e:
            logger.error(f"Error handling approval: {str(e)}", exc_info=True)
            yield {"error": str(e), "thread_id": self.thread_id}

    async def stop_agent(self) -> dict:
        """Stop the agent execution"""
        try:
            # Signal to environments to stop
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
        self.current_state = None


def serialize_graph_response(data: Any) -> Any:
    """Convert any object to a JSON-serializable format"""

    # Handle BaseModel instances
    if isinstance(data, BaseModel):
        return data.model_dump()

    # Handle dictionaries
    elif isinstance(data, dict):
        # Skip __interrupt__ key which contains non-serializable objects
        return {
            key: serialize_graph_response(value)
            for key, value in data.items()
            if key != "__interrupt__"
        }

    # Handle lists
    elif isinstance(data, list):
        return [serialize_graph_response(item) for item in data]

    # Handle tuples
    elif isinstance(data, tuple):
        return [serialize_graph_response(item) for item in data]

    # Handle sets
    elif isinstance(data, set):
        return [serialize_graph_response(item) for item in data]

    # Handle other potentially non-serializable objects
    try:
        # Try to convert to string if basic serialization fails
        import json

        json.dumps(data)
        return data
    except (TypeError, OverflowError):
        return str(data)
