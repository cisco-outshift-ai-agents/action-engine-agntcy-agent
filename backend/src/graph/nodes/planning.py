import logging
from typing import Dict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.graph.environments.planning import PlanningEnvironment
from src.graph.nodes.base_node import BaseNode
from src.graph.prompts import get_planner_prompt
from src.graph.types import AgentState
from tools.planning import planning_tool
from tools.terminate import terminate_tool
from tools.tool_collection import ActionEngineToolCollection
from tools.utils import hydrate_messages, serialize_messages

logger = logging.getLogger(__name__)


class PlanningNode(BaseNode):
    """Provides high-level guidance but doesn't control execution flow"""

    def __init__(self):
        self.name = "planning"
        self.tool_collection = ActionEngineToolCollection([planning_tool])

    async def ainvoke(self, state: AgentState, config: Dict = None) -> AgentState:
        logger.info("PlanningNode invoked")
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

        bound_llm = llm.bind_tools(
            self.tool_collection.get_tools(), tool_choice="auto"
        ).with_config(config=config)

        # Add system message first
        local_messages = []
        planner_prompt = get_planner_prompt()
        system_message = SystemMessage(content=planner_prompt)
        local_messages.append(system_message)

        # Hydrate existing messages
        hydrated = hydrate_messages(state["messages"])
        hydrated = self.prune_messages(hydrated)
        local_messages.extend(hydrated)

        # Add new human message with the task
        human_message = HumanMessage(content=state["task"])
        local_messages.append(human_message)

        # Add the current plan message
        plan_msg = planning_env.get_message_for_current_plan()
        local_messages.append(plan_msg)

        # Get LLM response with tool calls
        raw_response: AIMessage = await self.call_model_with_tool_retry(
            llm=bound_llm, messages=local_messages
        )
        if not raw_response:
            raise ValueError("LLM response not provided")

        # Add planner identity to response
        prefixed_content = f"[Planning Node] Based on the current state, I am updating the plan:\n{raw_response.content}"
        response = AIMessage(
            content=prefixed_content,
            tool_calls=(
                raw_response.tool_calls if hasattr(raw_response, "tool_calls") else None
            ),
        )

        # First hydrate any existing messages before serializing
        existing_messages = hydrate_messages(state["messages"])
        global_messages = serialize_messages(existing_messages)
        global_messages.extend(serialize_messages([response]))

        # Execute any tool calls and add the tool messages to the global state
        if hasattr(raw_response, "tool_calls") and raw_response.tool_calls:
            logger.info(f"Executing tool calls: {response.tool_calls}")
            tool_messages = await self.execute_tools(message=response, config=config)
            global_messages.extend(serialize_messages(tool_messages))

        # Update plan in state if available
        plan = planning_env.get_plan()
        if plan:
            state["plan"] = plan.to_dict()
        else:
            state["plan"] = None

        # Update the global state with the new messages
        state["messages"] = global_messages
        return state
