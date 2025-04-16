import json
import logging
from typing import Any, Dict, List

from langchain_core.messages import (
    AIMessage,
)
from langchain_openai import ChatOpenAI

from src.graph.environments.planning import PlanningEnvironment
from src.graph.nodes.base_node import BaseNode
from src.graph.prompts import get_executor_prompt, get_previous_tool_calls_prompt
from src.graph.types import AgentState
from tools.browser_use import browser_use_tool
from tools.terminal import terminal_tool
from tools.terminate import terminate_tool
from tools.tool_collection import ActionEngineToolCollection
from tools.utils import (
    get_executor_system_prompt_context,
    hydrate_messages,
    serialize_messages,
)

logger = logging.getLogger(__name__)


class ExecutorNode(BaseNode):
    """Executes tools in a LangGraph workflow"""

    def __init__(self):
        self.name = "executor"
        self.tool_collection = ActionEngineToolCollection(
            [
                terminal_tool,
                browser_use_tool,
                terminate_tool,
            ]
        )

    async def ainvoke(self, state: AgentState, config: Dict) -> Dict:
        """Async invocation with direct tool execution of approved tools"""
        logger.info("ExecutorNode invoked")

        if "messages" not in state:
            state["messages"] = []
            logger.debug("Initialized empty messages list in state")

        # Initialize global_messages
        existing_messages = hydrate_messages(state["messages"])
        global_messages = serialize_messages(existing_messages)

        # Get the approved tool call from pending_approval
        pending_approval = state.get("pending_approval", {})
        tool_call = pending_approval.get("tool_call")

        if not tool_call or not pending_approval.get("approved", False):
            logger.info("No approved tool call to execute")
            return state

        logger.info(f"Executing approved tool call: {tool_call}")

        # Create an AIMessage with the approved tool call
        execute_message = AIMessage(
            content="[Executor Node] Executing approved action",
            tool_calls=[tool_call],
        )
        global_messages.extend(serialize_messages([execute_message]))

        # Execute the approved tool call
        tool_messages = await self.execute_tools(message=execute_message, config=config)
        global_messages.extend(serialize_messages(tool_messages))

        # Check for termination tool call
        if tool_call.get("name") == "terminate":
            state["exiting"] = True
            state["thought"] = tool_call["args"]["reason"]

        # Clear pending_approval and tool_calls after execution
        state["pending_approval"] = {}
        state["tool_calls"] = []

        # Update the global state with the new messages
        state["messages"] = global_messages
        return state
