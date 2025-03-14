import logging
from typing import Dict, List, Any
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_openai import ChatOpenAI

from graph.types import AgentState
from tools.tool_collection import ActionEngineToolCollection
from tools.terminal import terminal_tool
from tools.file_saver import file_saver_tool
from tools.browser_use import browser_use_tool
from tools.google_search import google_search_tool
from tools.python_execute import python_execute_tool
from tools.str_replace_editor import str_replace_editor_tool
from tools.terminate import terminate_tool
from tools.utils import (
    deserialize_messages,
    serialize_messages,
    get_environment_system_prompt_context,
)
from graph.prompts import get_environment_prompt

logger = logging.getLogger(__name__)


class ExecutorNode:
    """Executes tools in a LangGraph workflow"""

    def __init__(self):
        self.name = "executor"
        self.tool_collection = ActionEngineToolCollection(
            [
                terminal_tool,
                file_saver_tool,
                browser_use_tool,
                google_search_tool,
                python_execute_tool,
                str_replace_editor_tool,
                terminate_tool,
            ]
        )

    async def __call__(self, state: AgentState, config: Dict):
        """Make node callable for LangGraph and ensure async execution"""
        return await self.ainvoke(state, config)

    async def ainvoke(self, state: AgentState, config: Dict) -> Dict:
        """Async invocation with direct tool execution"""
        if "messages" not in state:
            state["messages"] = []
            logger.debug("Initialized empty messages list in state")

        if not config:
            logger.debug("Config not provided in ExecutorNode")
            raise ValueError("Config not provided in ExecutorNode")

        environment_prompt_context = await get_environment_system_prompt_context(
            config=config
        )
        if not environment_prompt_context:
            raise ValueError("System prompt context not provided in config")

        environment_prompt = get_environment_prompt(context=environment_prompt_context)

        llm: ChatOpenAI = config.get("configurable", {}).get("llm")
        if not llm:
            raise ValueError("LLM not provided in config")

        # Bind tools to LLM
        bound_llm = llm.bind_tools(self.tool_collection.get_tools()).with_config(
            config=config
        )

        # Deserialize existing messages
        messages = deserialize_messages(state["messages"])

        # Add environment prompt
        environment_message = SystemMessage(content=environment_prompt)
        messages.append(environment_message)

        # Add new human message
        human_message = HumanMessage(content=state["task"])
        messages.append(human_message)

        # Get LLM response with tool calls
        response: AIMessage = await bound_llm.ainvoke(messages)

        # Serialize messages for state storage
        serialized_messages = serialize_messages(messages)
        serialized_messages.extend(serialize_messages([response]))

        # Execute any tool calls
        if hasattr(response, "tool_calls") and response.tool_calls:
            tool_messages = await self.execute_tools(message=response, config=config)
            serialized_messages.extend(serialize_messages(tool_messages))

        termination_tool_call = next(
            (tc for tc in response.tool_calls if tc["name"] == "terminate"), None
        )
        if termination_tool_call:
            state["exiting"] = True
            state["thought"] = termination_tool_call["reason"]

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

                # Pass the config separately - let tool_collection handle merging
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
                tool_messages.append(
                    ToolMessage(
                        tool_name=tool_call.function.name,
                        content=str(e),
                        tool_call_id=tool_call.id,
                    )
                )

        return tool_messages
