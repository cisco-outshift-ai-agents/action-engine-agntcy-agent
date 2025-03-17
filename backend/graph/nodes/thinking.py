import logging
import json
from typing import Dict, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage

from graph.types import AgentState, BrainState

from tools.tool_collection import ActionEngineToolCollection
from tools.terminate import terminate_tool
from tools.utils import deserialize_messages, serialize_messages
from graph.prompts import get_thinking_prompt
from graph.environments.planning import PlanningEnvironment

logger = logging.getLogger(__name__)


class ThinkingNode:
    """Prepares the user-centric thoughts and responses given the brain
    state"""

    def __init__(self):
        self.name = "thinking"

    async def __call__(self, state: AgentState, config: Dict):
        """Make node callable for LangGraph and ensure async execution"""
        return await self.ainvoke(state, config)

    def invoke(self, state: AgentState, config: Dict):
        """Prevent sync execution"""
        raise NotImplementedError("Chain of thought requires async execution")

    async def ainvoke(self, state: AgentState, config: Dict = None) -> AgentState:

        if "messages" not in state:
            state["messages"] = []
            logger.debug("Initialized empty messages list in state")

        if not config:
            logger.debug("Config not provided in PlanningNode")
            raise ValueError("Config not provided")

        planning_env = config["configurable"].get("planning_environment")
        if not isinstance(planning_env, PlanningEnvironment):
            logger.error("No planning_environment in configurable")
            return ValueError("Planning environment not initialized")

        llm: ChatOpenAI = config.get("configurable", {}).get("llm")

        structured_llm = llm.with_structured_output(BrainState)

        # Deserialize existing messages
        messages = deserialize_messages(state["messages"])

        # Add new system message
        thinking_prompt = get_thinking_prompt(state["brain"])
        system_message = SystemMessage(content=thinking_prompt)
        messages.append(system_message)

        # Add new human message
        human_message = HumanMessage(content=state["task"])
        messages.append(human_message)

        # Add the plan message
        plan_msg = planning_env.get_ai_message_for_current_plan()
        messages.append(plan_msg)

        # Get LLM response
        _response = await structured_llm.ainvoke(messages)
        response = BrainState(**_response.dict())
        state["thought"] = response.thought
        state["summary"] = response.summary
        state["brain"] = response
        brain_state_message = AIMessage(content=json.dumps(response.model_dump()))

        # Serialize messages for state storage
        serialized_messages = serialize_messages(messages)
        serialized_messages.extend(serialize_messages([brain_state_message]))

        state["messages"] = serialized_messages
        return state
