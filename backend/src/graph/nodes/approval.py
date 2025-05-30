import logging
from typing import Dict, List, Optional
from langgraph.types import interrupt
from langchain_core.messages import AIMessage, ToolMessage
from src.graph.nodes.base_node import BaseNode
from src.graph.types import AgentState, WorkableToolCall

logger = logging.getLogger(__name__)


class HumanApprovalNode(BaseNode):
    """Node to handle human-in-the-loop approval requests"""

    async def ainvoke(self, state: AgentState, config: dict) -> AgentState:
        logger.info("Human in the loop Node invoked")

        # Get tool calls from state and check if there's a terminate tool call
        tool_calls = state.get("tool_calls", [])
        if tool_calls:
            state["pending_approval"] = {}
        terminate_call = next(
            (tc for tc in tool_calls if tc.get("name") == "terminate"), None
        )

        if terminate_call:
            logger.info(f"Found termination call: {terminate_call}")

            # Instead of immediately exiting, approve the terminate tool to let it go to the executor node
            state["pending_approval"] = {
                "tool_call": terminate_call,
                "approved": True,
            }

            # Remove from tool_calls to avoid duplication
            state["tool_calls"] = []
            return state

        # Check if there is an existing pending_approval and skip if already approved
        pending_approval = state.get("pending_approval", {})
        if pending_approval.get("approved", False):
            logger.info("Found approved tool call, passing to executor")
            return state

        # Check if there is a terminal command that needs approval and interrupt
        for tool_call in tool_calls:
            if tool_call.get("name") == "terminal":
                logger.info(f"Found terminal command, requesting approval: {tool_call}")
                script = tool_call.get("args", {}).get("script", "N/A")

                state["pending_approval"] = {"tool_call": tool_call, "approved": False}
                interrupt_data = {
                    "tool_call": tool_call,
                    "message": f"Do you approve executing the terminal command: '{script}'?",
                }
                return interrupt(interrupt_data)

        # For any other tools (like browser_use), just let them pass through
        logger.info("No terminal commands found, automatic approval for other tools")
        for tool_call in tool_calls:
            if tool_call.get("name") not in ["terminal", "terminate"]:
                state["pending_approval"] = {"tool_call": tool_call, "approved": True}
                break

        return state
