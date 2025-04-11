import json
import logging
from typing import Any, Dict, List

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_openai import ChatOpenAI

from src.graph.environments.planning import PlanningEnvironment
from src.graph.nodes.base_node import BaseNode
from src.graph.prompts import get_executor_prompt, get_previous_tool_calls_prompt
from src.graph.types import AgentState, WorkableToolCall
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
    """Executes previously approved tools in a LangGraph workflow"""

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

        # Get approved tool calls
        approved_tool_calls = state.get("approved_tool_calls", [])

        if not approved_tool_calls:
            logger.info("No approved tool calls to execute")
            return state

        logger.info(f"Executing approved tool calls: {approved_tool_calls}")

        # Create an AIMessage with the approved tool calls
        execute_message = AIMessage(
            content="[Executor Node] Executing approved actions",
            tool_calls=approved_tool_calls,
        )

        # Execute the approved tool calls
        tool_messages = await self.execute_tools(message=execute_message, config=config)

        # Add messages to state
        existing_messages = hydrate_messages(state["messages"])
        global_messages = serialize_messages(existing_messages)
        global_messages.extend(serialize_messages([execute_message]))
        global_messages.extend(serialize_messages(tool_messages))

        # Clear approved tool calls
        state["approved_tool_calls"] = []

        # Update the global state with the new messages
        state["messages"] = global_messages
        return state
