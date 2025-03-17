import logging
import json
from typing import Dict
from langchain_openai import ChatOpenAI
from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    SystemMessage,
)

from graph.types import AgentState
from tools.tool_collection import ActionEngineToolCollection
from tools.planning import planning_tool
from tools.terminate import terminate_tool
from tools.utils import hydrate_messages, serialize_messages
from graph.prompts import get_planner_prompt
from graph.environments.planning import PlanningEnvironment
from graph.nodes.base_node import BaseNode

logger = logging.getLogger(__name__)


class PlanningNode(BaseNode):
    """Provides high-level guidance but doesn't control execution flow"""

    def __init__(self):
        self.name = "planning"
        self.tool_collection = ActionEngineToolCollection(
            [planning_tool, terminate_tool]
        )

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

        bound_llm = llm.bind_tools(self.tool_collection.get_tools()).with_config(
            config=config
        )

        ## Manage two running states of messages:
        ## 1. Local messages: Messages that are only relevant to the current node, pruned from global message state
        ##      and are sent to the LLM
        ## 2. Global messages: Long term message store that is relevant to the entire conversation and are
        ##      stored in the global state

        # Hydrate existing messages
        local_messages = hydrate_messages(state["messages"])
        local_messages = self.prune_messages(local_messages)

        # Add new human message with the task
        human_message = HumanMessage(content=state["task"])
        local_messages.append(human_message)

        # Add new system message for this node
        planner_prompt = get_planner_prompt()
        system_message = SystemMessage(content=planner_prompt)
        local_messages.append(system_message)

        # Add the current plan message
        plan_msg = planning_env.get_ai_message_for_current_plan()
        local_messages.append(plan_msg)

        # Get LLM response with tool calls
        response: AIMessage = await bound_llm.ainvoke(local_messages)

        # First hydrate any existing messages before serializing
        existing_messages = hydrate_messages(state["messages"])
        global_messages = serialize_messages(existing_messages)
        global_messages.extend(
            serialize_messages([human_message, system_message, plan_msg, response])
        )

        # Execute any tool calls and add the tool messages to the global state
        if hasattr(response, "tool_calls") and response.tool_calls:
            tool_messages = await self.execute_tools(message=response)
            global_messages.extend(serialize_messages(tool_messages))

        # Check for and handle termination tool call
        termination_tool_call = next(
            (tc for tc in response.tool_calls if tc["name"] == "terminate"), None
        )
        if termination_tool_call:
            state["exiting"] = True
            state["thought"] = termination_tool_call["reason"]

        # Update the global state with the new messages
        state["messages"] = global_messages
        return state
