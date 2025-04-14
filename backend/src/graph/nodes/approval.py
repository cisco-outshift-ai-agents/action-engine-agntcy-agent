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

        # Check if there is a pending approval decision
        pending_approval = state.get("pending_approval", {})
        if pending_approval.get("approved", False):
            logger.info("Found approved tool call, no need for further interruption")

            # Ensure the tool call is in approved_tool_calls
            if "approved_tool_calls" not in state:
                state["approved_tool_calls"] = []

            # Only add if not already present (avoid duplicates)
            tool_call = pending_approval.get("tool_call")
            if tool_call and tool_call not in state["approved_tool_calls"]:
                logger.info(
                    f"Adding previously approved tool call to approved_tool_calls: {tool_call}"
                )
                state["approved_tool_calls"].append(tool_call)

            # Clear pending_tool_calls to avoid reprocessing
            state["pending_tool_calls"] = []

            return state

        # Get pending tool calls from state. If no pending_tool_calls, extract them from messages

        pending_tool_calls = state.get("pending_tool_calls", [])

        if not pending_tool_calls and "messages" in state:
            logger.info("No pending_tool_calls found in state, checking messages")
            messages = state["messages"]

            # Look for the most recent AIMessage with tool calls
            for message in reversed(messages):
                if message.get("type") == "AIMessage" and "tool_calls" in message:
                    for tool_call in message.get("tool_calls", []):
                        pending_tool_calls.append(tool_call)
                        logger.info(f"Found tool call in messages: {tool_call}")

                    # Only look at the most recent message with tool calls
                    if pending_tool_calls:
                        break

            state["pending_tool_calls"] = pending_tool_calls

        terminal_calls = [
            tool_call
            for tool_call in pending_tool_calls
            if tool_call.get("name") == "terminal"
        ]
        non_terminal_calls = [
            tool_call
            for tool_call in pending_tool_calls
            if tool_call.get("name") != "terminal"
        ]

        if terminal_calls:
            tool_call = terminal_calls[0]
            logger.info(f"Raising HITL interrupt for terminal action: {tool_call}")
            script = tool_call.get("args", {}).get("script", "N/A")
            terminal_id = tool_call.get("args", {}).get("terminal_id", "unknown")

            # Set a flag in state to track that this was approved
            state["pending_approval"] = {"tool_call": tool_call, "approved": False}

            interrupt_data = {
                "tool_call": tool_call,
                "message": f"Do you approve executing the terminal command: '{script}'?",
                "terminal_id": terminal_id,
            }

            return interrupt(interrupt_data)

        if non_terminal_calls:
            logger.info("Only non-terminal tool calls found, auto-approving")
            state["approved_tool_calls"] = non_terminal_calls
            state["pending_tool_calls"] = []
            logger.info(f"Final approved tool calls: {state['approved_tool_calls']}")
            return state

        logger.info("No tool calls found. Nothing to approve.")
        return state
