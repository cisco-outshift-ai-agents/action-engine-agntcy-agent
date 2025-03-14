import json
import logging
from typing import Dict

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from core.types import AgentState

from ..prompts import format_message_history  # Updated import path
from ..prompts import get_chain_of_thought_prompt

logger = logging.getLogger(__name__)


class PlanningNode:
    """Provides high-level guidance but doesn't control execution flow"""

    def __init__(self):
        self.name = "planning"

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

        # Build context from previous brain states
        context = []
        if state.get("messages"):
            formatted_history = format_message_history(state["messages"])
            context.append(formatted_history)
        else:
            logger.debug("No previous messages found for context building")

        context_text = "\n".join(context)
        logger.info(f"Built context with {len(context)} entries")

        messages = [
            HumanMessage(content=state["task"]),
            SystemMessage(
                content=get_chain_of_thought_prompt(
                    task=state["task"],
                    context=context_text,
                    todo_list=state.get("todo_list", []),
                )
            ),
        ]

        structured_llm = llm.with_structured_output(ChainOfThought)
        response = await structured_llm.ainvoke(messages)
        logger.info(f"ChainOfThoughtNode: Response: {response.model_dump()}")

        state["todo_list"] = response.todo_list
        return state


class ChainOfThought(BaseModel):
    """Simple chain of thought response"""

    todo_list: str = Field(
        description="""
    The updated Todo list for the users task.
    Format the todo list as a series of checklist items, formatted like '- [ ] item'.  
    As the user completes items, check them off by changing the item to '- [✓] item'."
    """
    )
