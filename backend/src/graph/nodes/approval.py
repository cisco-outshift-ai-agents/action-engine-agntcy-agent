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

        # Get pending tool calls from state
        pending_tool_calls = state.get("pending_tool_calls", [])
        logger.info(f"Found {len(pending_tool_calls)} pending_tool_calls in state.")

        # If no pending_tool_calls in state, extract them from the messages
        terminal_tool_calls = []

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

            # If we found tool calls in messages, add them to pending_tool_calls
            if terminal_tool_calls:
                pending_tool_calls = terminal_tool_calls
                # Update state with the extracted tool calls
                state["pending_tool_calls"] = pending_tool_calls

        # Now check all the pending tool calls for terminal commands
        for tool_call in pending_tool_calls:
            if tool_call.get("name") == "terminal":
                logger.info(f"Raising HITL interrupt for terminal action: {tool_call}")
                script = tool_call.get("args", {}).get("script", "N/A")
                terminal_id = tool_call.get("args", {}).get("terminal_id", "N/A")

                # Set a flag in state to track that this was approved
                state["pending_approval"] = {"tool_call": tool_call, "approved": False}

                # Create a data dict with both original data and type information
                data = {
                    "tool_call": tool_call,
                    "message": f"Do you approve executing the terminal command: '{script}' on terminal {terminal_id}?",
                    "__interrupt_type": "approval_request",  # Add type as part of data
                }

                # LangGraph's interrupt() function doesn't accept 'type' parameter
                # It only accepts a data parameter
                raise interrupt(data)

        logger.info("No terminal tool call found, skipping HITL")

        # If we reach here, there were no terminal commands or they were all approved
        # Mark all pending tool calls as approved
        state["approved_tool_calls"] = pending_tool_calls
        state["pending_tool_calls"] = []

        return state

    def decide_next_node(self, state: AgentState) -> str:
        """Determine the next node based on approval state"""
        pending_approval = state.get("pending_approval", {})

        if pending_approval.get("approved", False):
            # User approved the action
            tool_call = pending_approval.get("tool_call")
            if tool_call:
                # Move from pending to approved
                state["approved_tool_calls"] = state.get("approved_tool_calls", []) + [
                    tool_call
                ]
                state["pending_tool_calls"] = [
                    tc for tc in state.get("pending_tool_calls", []) if tc != tool_call
                ]
            return "executor"
        else:
            # User denied, go back to thinking/planning
            state["pending_tool_calls"] = []
            return "thinking"
