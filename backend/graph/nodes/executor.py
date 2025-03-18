import logging
from typing import Dict, List, Any
from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    ToolMessage,
    BaseMessage,
    SystemMessage,
)
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
    serialize_messages,
    get_executor_system_prompt_context,
    hydrate_messages,
)
from graph.prompts import get_executor_prompt
from graph.nodes.base_node import BaseNode

logger = logging.getLogger(__name__)


class ExecutorNode(BaseNode):
    """Executes tools in a LangGraph workflow"""

    def __init__(self):
        self.name = "executor"
        self.tool_collection = ActionEngineToolCollection(
            [
                terminal_tool,
                # file_saver_tool,
                browser_use_tool,
                # google_search_tool,
                # python_execute_tool,
                # str_replace_editor_tool,
                terminate_tool,
            ]
        )

    async def ainvoke(self, state: AgentState, config: Dict) -> Dict:
        """Async invocation with direct tool execution"""
        logger.info("ExecutorNode invoked")

        if "messages" not in state:
            state["messages"] = []
            logger.debug("Initialized empty messages list in state")

        if not config:
            logger.debug("Config not provided in ExecutorNode")
            raise ValueError("Config not provided in ExecutorNode")

        llm: ChatOpenAI = config.get("configurable", {}).get("llm")
        if not llm:
            raise ValueError("LLM not provided in config")

        # Bind tools to LLM
        bound_llm = llm.bind_tools(
            self.tool_collection.get_tools(), tool_choice="auto"
        ).with_config(config=config)

        # Hydrate existing messages
        local_messages = hydrate_messages(state["messages"])
        local_messages = self.prune_messages(local_messages)

        # Add new human message with the task
        human_message = HumanMessage(content=state["task"])
        local_messages.append(human_message)

        # Add environment prompt
        executor_prompt_context = await get_executor_system_prompt_context(
            config=config
        )
        if not executor_prompt_context:
            raise ValueError("System prompt context not provided in config")

        executor_prompt = get_executor_prompt(context=executor_prompt_context)
        screenshot = executor_prompt_context.screenshot
        executor_message = SystemMessage(
            content=[
                {"type": "text", "text": executor_prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{screenshot}"},
                },
            ]
        )
        local_messages.append(executor_message)

        # Get LLM response with tool calls
        response: AIMessage = await self.call_model_with_tool_retry(
            llm=bound_llm, messages=local_messages
        )
        if not response:
            raise ValueError("LLM response not provided")

        # First hydrate any existing messages before serializing
        existing_messages = hydrate_messages(state["messages"])
        global_messages = serialize_messages(existing_messages)
        global_messages.extend(
            # serialize_messages([human_message, executor_message, response])
            serialize_messages([response])
        )

        # Execute any tool calls
        if hasattr(response, "tool_calls") and response.tool_calls:
            logger.info(f"Executing tool calls: {response.tool_calls}")
            tool_messages = await self.execute_tools(message=response, config=config)
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
