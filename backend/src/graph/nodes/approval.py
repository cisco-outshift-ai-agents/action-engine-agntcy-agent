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

        # Check for termination first - We need to look at tool_calls before anything else
        tool_calls = state.get("tool_calls", [])
        for tool_call in tool_calls:
            if tool_call.get("name") == "terminate":
                logger.info(f"Found termination call, exiting immediately: {tool_call}")
                # Set exiting flag
                state["exiting"] = True
                # Set thought for display
                state["thought"] = tool_call.get("args", {}).get(
                    "reason", "Task completed"
                )
                # Clear all other state that might cause additional executions
                state["tool_calls"] = []
                state["pending_approval"] = {}
                return state

        # Check if there is an existing pending_approval
        pending_approval = state.get("pending_approval", {})

        # If the pending approval is already marked as approved, just pass through
        if pending_approval.get("approved", False):
            logger.info("Found approved tool call, passing to executor")
            return state

        # Check if there is a terminate tool call
        tool_calls = state.get("tool_calls", [])
        for tool_call in tool_calls:
            if tool_call.get("name") == "terminate":
                logger.info(f"Found termination call, setting exiting: {tool_call}")
                state["exiting"] = True
                state["thought"] = tool_call.get("args", {}).get(
                    "reason", "Task completed"
                )
                return state

        # Check if there is a terminal command that needs approval
        for tool_call in tool_calls:
            if tool_call.get("name") == "terminal":
                logger.info(f"Found terminal command, requesting approval: {tool_call}")
                script = tool_call.get("args", {}).get("script", "N/A")

                # Set pending approval with this tool
                state["pending_approval"] = {"tool_call": tool_call, "approved": False}

                # Interrupt for approval
                interrupt_data = {
                    "tool_call": tool_call,
                    "message": f"Do you approve executing the terminal command: '{script}'?",
                }
                return interrupt(interrupt_data)

        # For any other tools (like browser_use), just let them pass through
        logger.info("No terminal commands found, automatic approval for other tools")
        # Store the first non-terminal tool in pending_approval for executor to use
        for tool_call in tool_calls:
            if tool_call.get("name") not in ["terminal", "terminate"]:
                state["pending_approval"] = {"tool_call": tool_call, "approved": True}
                break

        return state
