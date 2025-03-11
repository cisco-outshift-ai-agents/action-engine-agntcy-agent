import logging
from typing import Dict
from langchain_core.messages import SystemMessage, HumanMessage
from core.types import AgentState, BrainState  # Update import to use core.types

logger = logging.getLogger(__name__)


class ChainOfThoughtNode:
    """Provides high-level guidance but doesn't control execution flow"""

    def __init__(self):
        self.name = "chain_of_thought"

    async def __call__(self, state: AgentState, config: Dict):
        """Make node callable for LangGraph and ensure async execution"""
        return await self.ainvoke(state, config)

    def invoke(self, state: AgentState, config: Dict):
        """Prevent sync execution"""
        raise NotImplementedError("Chain of thought requires async execution")

    async def ainvoke(self, state: AgentState, config: Dict) -> AgentState:
        """Think about current state and provide guidance"""
        logger.info("ChainOfThoughtNode: Starting execution")
        llm = config.get("configurable", {}).get("llm")
        if not llm:
            raise ValueError("LLM not provided in config")

        messages = [
            HumanMessage(content=state["task"]),
            SystemMessage(
                content="Think about how to accomplish this task. What tools or approaches might help?"
            ),
        ]

        response = await llm.ainvoke(messages)

        logger.info(f"ChainOfThoughtNode: Thought: {response.content}")

        # Update brain state with thoughts but don't control flow
        state["brain"] = BrainState(
            thought=response.content,
            summary=_generate_summary(state),
        ).model_dump()

        return state


def _generate_summary(state: AgentState) -> str:
    """Generate action summary"""
    current_env = state.get("current_env", "")
    return f"Using {current_env} to complete task: {state.get('task', '')}"
