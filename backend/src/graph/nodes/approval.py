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
        logger.info(f"State keys in HITL node: {list(state.keys())}")

        # Print full structure of state for debugging
        logger.info("HumanApprovalNode full state:")
        for k, v in state.items():
            logger.info(f"  {k}: {type(v)} -> {v}")

        # Check if we already have a pending approval decision
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

        # Get pending tool calls from state or messages
        terminal_tool_calls = []

        # First try to get from pending_tool_calls
        pending_tool_calls = state.get("pending_tool_calls", [])

        # If no pending_tool_calls, extract from messages
        if not pending_tool_calls and "messages" in state:
            logger.info("No pending_tool_calls found in state, checking messages")
            messages = state["messages"]

            # Look for the most recent AIMessage with terminal tool calls
            for message in reversed(messages):
                if message.get("type") == "AIMessage" and "tool_calls" in message:
                    for tool_call in message.get("tool_calls", []):
                        if tool_call.get("name") == "terminal":
                            terminal_tool_calls.append(tool_call)
                            logger.info(
                                f"Found terminal tool call in messages: {tool_call}"
                            )

                    # Only look at the most recent message with tool calls
                    if terminal_tool_calls:
                        break

            # If we found tool calls in messages, use those
            if terminal_tool_calls:
                pending_tool_calls = terminal_tool_calls
                # Update state with the extracted tool calls
                state["pending_tool_calls"] = pending_tool_calls

        # Check for terminal commands in all pending tool calls
        for tool_call in pending_tool_calls:
            if tool_call.get("name") == "terminal":
                logger.info(f"Raising HITL interrupt for terminal action: {tool_call}")
                script = tool_call.get("args", {}).get("script", "N/A")
                terminal_id = tool_call.get("args", {}).get("terminal_id", "unknown")

                # Set a flag in state to track that this was approved
                state["pending_approval"] = {"tool_call": tool_call, "approved": False}

                # Create a simple interrupt with just the essential information
                interrupt_data = {
                    "tool_call": tool_call,
                    "message": f"Do you approve executing the terminal command: '{script}'?",
                    "terminal_id": terminal_id,
                }

                # Instead of raising it as an exception, return it as an interrupt signal
                return interrupt(interrupt_data)

        logger.info("No terminal tool call found, skipping HITL")

        # If we reach here, there were no terminal commands or they were all approved
        # Mark all pending tool calls as approved
        state["approved_tool_calls"] = pending_tool_calls
        state["pending_tool_calls"] = []

        return state
