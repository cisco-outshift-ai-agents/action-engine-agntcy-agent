import logging
from typing import Dict, List

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain.chat_models.base import BaseChatModel

from src.graph.environments.planning import PlanningEnvironment
from src.graph.nodes.base_node import BaseNode
from src.graph.prompts import get_executor_prompt, get_previous_tool_calls_prompt
from src.graph.types import AgentState
from src.tools.browser_use import browser_use_tool
from src.tools.terminal import terminal_tool
from src.tools.terminate import terminate_tool
from src.tools.tool_collection import ActionEngineToolCollection
from src.tools.utils import (
    get_executor_system_prompt_context,
    hydrate_messages,
    serialize_messages,
)

logger = logging.getLogger(__name__)


class ToolGeneratorNode(BaseNode):
    """Selects tools but does not execute them, for review by HumanApprovalNode"""

    def __init__(self):
        self.name = "tool_generator"
        self.tool_collection = ActionEngineToolCollection(
            [
                terminal_tool,
                browser_use_tool,
                terminate_tool,
            ]
        )

    async def ainvoke(self, state: AgentState, config: Dict) -> Dict:
        """Async invocation with tool generator but without execution"""
        logger.info("ToolGeneratorNode invoked")

        if "messages" not in state:
            state["messages"] = []
            logger.debug("Initialized empty messages list in state")

        if not config:
            logger.debug("Config not provided in ToolGeneratorNode")
            raise ValueError("Config not provided in ToolGeneratorNode")

        llm: BaseChatModel = config.get("configurable", {}).get("llm")
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
        tool_call_as_string = (
            str(raw_response.tool_calls) if hasattr(raw_response, "tool_calls") else ""
        )
        prefixed_content = (
            f"[Tool Generator Node] I am now selecting the next tool to use.\n"
            "The tool calls I am generating are:\n"
            f"{tool_call_as_string}\n"
        )
        response = AIMessage(
            content=prefixed_content,
            tool_calls=(
                raw_response.tool_calls if hasattr(raw_response, "tool_calls") else None
            ),
        )

        # Store generated tool calls for the approval node to use
        if hasattr(response, "tool_calls") and response.tool_calls:
            state["tool_calls"] = response.tool_calls
            logger.info(f"ToolGeneratorNode selected tool calls: {response.tool_calls}")
        else:
            state["tool_calls"] = []

        # First hydrate any existing messages before serializing
        existing_messages = hydrate_messages(state["messages"])
        global_messages = serialize_messages(existing_messages)
        global_messages.extend(serialize_messages([response]))

        # Update the global state with the new messages
        state["messages"] = global_messages
        return state
