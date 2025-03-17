import logging
import json
from typing import Dict, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage

from graph.types import AgentState, BrainState
from tools.tool_collection import ActionEngineToolCollection
from tools.planning import planning_tool
from tools.terminate import terminate_tool
from tools.utils import deserialize_messages, serialize_messages
from graph.prompts import get_planner_prompt
from graph.environments.planning import PlanningEnvironment

logger = logging.getLogger(__name__)


class PlanningNode:
    """Provides high-level guidance but doesn't control execution flow"""

    def __init__(self):
        self.name = "planning"
        self.tool_collection = ActionEngineToolCollection(
            [planning_tool, terminate_tool]
        )

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

        bound_llm = llm.bind_tools(self.tool_collection.get_tools()).with_config(
            config=config
        )

        # Deserialize existing messages
        messages = deserialize_messages(state["messages"])

        # Add new system message
        environment_prompt = get_planner_prompt()
        system_message = SystemMessage(content=environment_prompt)
        messages.append(system_message)

        # Add new human message
        human_message = HumanMessage(content=state["task"])
        messages.append(human_message)

        # Add the plan message
        plan_msg = planning_env.get_ai_message_for_current_plan()
        messages.append(plan_msg)

        # Get LLM response with tool calls
        response: AIMessage = await bound_llm.ainvoke(messages)

        # Serialize messages for state storage
        serialized_messages = serialize_messages(messages)
        serialized_messages.extend(serialize_messages([response]))

        # Execute any tool calls
        if hasattr(response, "tool_calls") and response.tool_calls:
            tool_messages = await self.execute_tools(message=response)
            serialized_messages.extend(serialize_messages(tool_messages))

        state["messages"] = serialized_messages
        return state

    async def execute_tools(
        self, message: AIMessage, config: Dict = None
    ) -> List[ToolMessage]:
        """Execute tools using tool collection"""
        tool_messages = []

        for tool_call in message.tool_calls:
            try:
                name = tool_call["name"]
                args = tool_call["args"]

                if not name:
                    raise ValueError("Tool call missing function")

                # Explicitly create the tool input with config
                result = await self.tool_collection.execute_tool(
                    name=name,
                    input_dict=args,
                    config=config,
                )
                random_id = str(hash(str(tool_call) + str(result)))[:8]

                tool_messages.append(
                    ToolMessage(
                        tool_name=name,
                        content=str(result),
                        tool_call_id=random_id,
                    )
                )
            except Exception as e:
                logger.error(f"Error executing tool {tool_call}: {str(e)}")
                random_id = str(hash(str(tool_call) + str(result)))[:8]
                tool_messages.append(
                    ToolMessage(
                        tool_name=tool_call["name"],
                        content=str(e),
                        tool_call_id=random_id,
                    )
                )

        return tool_messages
