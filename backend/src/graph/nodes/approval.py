from langgraph.types import interrupt
from src.graph.nodes.base_node import BaseNode
from src.graph.types import AgentState


class HumanApprovalNode(BaseNode):
    """Node to handle human-in-the-loop approval requests"""

    async def ainvoke(self, state: AgentState, config: dict) -> AgentState:
        # Check if the next step requires terminal action
        if "tool_calls" in state and state["tool_calls"]:
            for tool_call in state["tool_calls"]:
                if tool_call["name"] == "terminal":
                    # Raise an interrupt for human approval
                    raise interrupt(
                        type="approval_request",
                        data={
                            "tool_call": tool_call,
                            "message": f"Do you approve executing the terminal action: {tool_call['args']['script']}?",
                        },
                    )
        return state
