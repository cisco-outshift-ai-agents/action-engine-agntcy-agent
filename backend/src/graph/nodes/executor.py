import json
import logging
from typing import Any, Dict, List

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_openai import ChatOpenAI

from src.graph.environments.planning import PlanningEnvironment
from src.graph.nodes.base_node import BaseNode
from src.graph.prompts import get_executor_prompt, get_previous_tool_calls_prompt
from src.graph.types import AgentState
from tools.browser_use import browser_use_tool
from tools.terminal import terminal_tool

# from tools.file_saver import file_saver_tool
# from tools.google_search import google_search_tool
# from tools.python_execute import python_execute_tool
# from tools.str_replace_editor import str_replace_editor_tool
from tools.terminate import terminate_tool
from tools.tool_collection import ActionEngineToolCollection
from tools.utils import (
    get_executor_system_prompt_context,
    hydrate_messages,
    serialize_messages,
)

logger = logging.getLogger(__name__)


class ExecutorNode(BaseNode):
    """Executes tools in a LangGraph workflow"""

    def __init__(self):
        self.name = "executor"
        self.tool_collection = ActionEngineToolCollection(
            [
                terminal_tool,
                browser_use_tool,
                terminate_tool,
                # file_saver_tool,
                # google_search_tool,
                # python_execute_tool,
                # str_replace_editor_tool,
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

        planning_env = config["configurable"].get("planning_environment")
        if not isinstance(planning_env, PlanningEnvironment):
            logger.error("No planning_environment in configurable")
            return ValueError("Planning environment not initialized")

        # Bind tools to LLM
        bound_llm = llm.bind_tools(
            self.tool_collection.get_tools(), tool_choice="auto"
        ).with_config(config=config)

        # Initialize with system message first
        local_messages = []
        executor_prompt_context = await get_executor_system_prompt_context(
            config=config
        )
        if not executor_prompt_context:
            raise ValueError("System prompt context not provided in config")

        # Add system message with current environment context
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

        # Hydrate and prune messages
        hydrated = hydrate_messages(state["messages"])
        hydrated = self.prune_messages(hydrated)
        local_messages.extend(hydrated)

        # Add task and plan context
        human_message = HumanMessage(content=state["task"])
        plan_msg = planning_env.get_message_for_current_plan()
        local_messages.extend([human_message, plan_msg])

        # Add context to prevent action repetition
        progress_context = HumanMessage(
            content=(
                "Based on the current state and plan above:\n"
                "1. Review what actions have already been completed\n"
                "2. Choose the next logical action that hasn't been done yet\n"
                "3. Do not repeat actions that were already successful\n"
                "4. Only use the tools which are available to you in the <tools></tools> XML structure."
                "\nWhat is the next action you should take?"
            )
        )
        local_messages.append(progress_context)

        # Get LLM response with tool calls
        raw_response: AIMessage = await self.call_model_with_tool_retry(
            llm=bound_llm, messages=local_messages
        )
        if not raw_response:
            raise ValueError("LLM response not provided")

        # Add executor identity to response
        prefixed_content = (
            f"[Executor Node] Based on the current system state, "
            f"I am choosing to: {raw_response.content}"
        )
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
            state["thought"] = json.loads(termination_tool_call["arguments"])["reason"]

        # Update the global state with the new messages
        state["messages"] = global_messages
        return state
