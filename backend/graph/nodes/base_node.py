import logging
import json
from typing import Dict, List, Optional
from langchain_core.messages import (
    AIMessage,
    ToolMessage,
    SystemMessage,
    BaseMessage,
    HumanMessage,
)
from graph.types import AgentState, WorkableToolCall
from tools.tool_collection import ActionEngineToolCollection
from langchain_openai import ChatOpenAI
from graph.prompts import get_tool_call_retry_prompt

logger = logging.getLogger(__name__)


class BaseNode:
    """Base class for all agent nodes"""

    name: str = "base"  # Default name, will be overridden by child classes
    tool_collection: ActionEngineToolCollection = None

    async def __call__(self, state: AgentState, config: Dict):
        """Make node callable for LangGraph and ensure async execution"""
        return await self.ainvoke(state, config)

    def invoke(self, state: AgentState, config: Dict):
        """Prevent sync execution"""
        raise NotImplementedError(f"{self.name} node requires async execution")

    async def execute_tools(
        self, message: AIMessage, config: Dict = None
    ) -> List[ToolMessage]:
        """Execute tools using tool collection"""
        tool_messages = []
        if not hasattr(message, "tool_calls") or not message.tool_calls:
            logger.warning("No tool_calls found in message")
            return tool_messages

        workable_tool_calls: List[WorkableToolCall] = self.get_workable_tool_calls(
            message
        )

        for tool_call in workable_tool_calls:
            try:
                name = tool_call.name
                args = tool_call.args
                call_id = tool_call.call_id

                if not name:
                    raise ValueError("Tool call missing function name")

                logger.info(f"Executing tool {name}")

                # Convert string args to dict if needed
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {"input": args}

                result = await self.tool_collection.execute_tool(
                    name=name,
                    input_dict=args,
                    config=config,
                )

                random_id = call_id or str(hash(str(tool_call) + str(result)))[:8]

                tool_messages.append(
                    ToolMessage(
                        tool_name=name,
                        content=str(result),
                        tool_call_id=random_id,
                    )
                )
            except Exception as e:
                logger.error(f"Error executing tool {tool_call}: {str(e)}")
                random_id = getattr(tool_call, "id", str(hash(str(tool_call)))[:8])
                tool_messages.append(
                    ToolMessage(
                        tool_name=name if name else "unknown",
                        content=str(e),
                        tool_call_id=random_id,
                    )
                )

        return tool_messages

    def prune_messages(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        """
        Prune messages to maintain a focused context while preserving important interactions.

        The pruning process:
        1. Removes system messages (these should be added fresh by each node)
        2. Removes empty messages
        3. Converts tool messages to AI messages for compatibility with vLLM
        4. Keeps the last 15 messages to maintain a reasonable context window

        Returns a list of pruned messages in chronological order.
        """
        beginning_length = len(messages)

        # Filter messages in one pass
        pruned_messages = []
        for msg in messages:
            # Skip system messages and empty messages
            if isinstance(msg, SystemMessage) or not msg.content:
                continue

            if isinstance(msg, ToolMessage):
                # Keep tool messages as passive observations
                pruned_messages.append(
                    AIMessage(
                        content=f"Observed event: Previous {msg.tool_name} action completed: {msg.content}"
                    )
                )
            else:
                # Keep all other non-empty messages
                pruned_messages.append(msg)

        # Keep the last 15 messages
        pruned_messages = pruned_messages[-15:]

        logger.info(
            f"Pruned {beginning_length - len(pruned_messages)} messages from {beginning_length} to {len(pruned_messages)}"
        )

        return pruned_messages

    async def call_model_with_tool_retry(
        self, llm: ChatOpenAI, messages: List[BaseMessage]
    ) -> AIMessage:
        """
        Call the model with the tool retry logic

        Since vLLM does not support tool_choice="required" (https://docs.vllm.ai/en/stable/features/tool_calling.html),
        we need to implement some retry logic to ensure that the model responds with the correct tool calls.
        """

        # Simple path - no tool collection means no validation needed
        if not self.tool_collection:
            logger.debug(
                f"{self.name} node has no tool collection, skipping validation"
            )
            return await llm.ainvoke(messages)

        # Tool validation path
        logger.debug(
            f"{self.name} node validating tools. Available: {self.tool_collection.list_tools()}"
        )

        MAX_ATTEMPTS = 5
        attempt = 0

        while attempt < MAX_ATTEMPTS:
            # Add retry prompt if needed
            if attempt > 0:
                logger.info(f"{self.name} node retrying, attempt {attempt}")
                available_tools = "\n".join(
                    f"- {tool} (available to {self.name} node)"
                    for tool in self.tool_collection.list_tools()
                )
                messages.append(
                    AIMessage(
                        content=get_tool_call_retry_prompt(tools_str=available_tools)
                    )
                )

            # Try to get valid tool calls
            attempt += 1
            try:
                response: AIMessage = await llm.ainvoke(messages)
                workable_tool_calls = self.get_workable_tool_calls(response)

                if len(workable_tool_calls) > 0:
                    tool_names = [tc.name for tc in workable_tool_calls]
                    logger.info(
                        f"{self.name} node got valid response with tools: {tool_names}"
                    )
                    return response

                # Only log non-empty invalid responses
                if response.content.strip():
                    logger.warning(
                        f"{self.name} node got response without valid tools: {response.content}"
                    )

            except Exception as e:
                logger.error(
                    f"Error in {self.name} node calling model with tool calls: {str(e)}"
                )
                continue

        return None

    def get_workable_tool_calls(self, message: AIMessage) -> List[WorkableToolCall]:
        """
        Convert tool calls to workable format, parsing out the necessary information
        regardless of whether the tool call is a dictionary or object.
        """
        all_tool_calls: List[WorkableToolCall] = []

        # First extract all potential tool calls
        for tool_call in message.tool_calls:
            if isinstance(tool_call, dict):
                all_tool_calls.append(
                    WorkableToolCall(
                        name=tool_call.get("name")
                        or tool_call.get("function", {}).get("name"),
                        args=tool_call.get("args")
                        or tool_call.get("function", {}).get("arguments"),
                        call_id=tool_call.get("id"),
                    )
                )
            else:
                all_tool_calls.append(
                    WorkableToolCall(
                        name=(
                            tool_call.function.name
                            if hasattr(tool_call, "function")
                            else tool_call.name
                        ),
                        args=(
                            tool_call.function.arguments
                            if hasattr(tool_call, "function")
                            else tool_call.args
                        ),
                        call_id=tool_call.id,
                    )
                )

        # Try to extract from message content
        extracted_text_tool_call = self.extract_workable_tool_call_from_vllm_string(
            message.content
        )
        if extracted_text_tool_call:
            all_tool_calls.append(extracted_text_tool_call)

        # Filter for only valid tools for this node
        if not self.tool_collection:
            logger.warning(
                f"{self.name} node has no tool collection, rejecting all tool calls"
            )
            return []

        available_tools = self.tool_collection.list_tools()
        valid_tool_calls = []
        for tc in all_tool_calls:
            if not tc.name:
                logger.warning(f"{self.name} node found tool call without name")
                continue

            if tc.name not in available_tools:
                logger.warning(
                    f"{self.name} node found unavailable tool: {tc.name}. "
                    f"Available tools are: {available_tools}"
                )
                continue

            valid_tool_calls.append(tc)

        if valid_tool_calls:
            logger.info(
                f"{self.name} node validated tool calls: {[tc.name for tc in valid_tool_calls]}"
            )

        return valid_tool_calls

    # Sometimes the tool call appears within the message itself
    # I think this is probably a bug with vLLM and the hermes parser
    # but we can handle it here while we wait for a fix
    def extract_workable_tool_call_from_vllm_string(
        self, string: str
    ) -> Optional[WorkableToolCall]:
        """
        Extract a tool call from a vLLM string if one exists.
        Validation against available tools happens in get_workable_tool_calls.
        """
        if not string or not isinstance(string, str):
            return None

        # Clean up any partial tool_call tags that might confuse the parser
        string = string.replace("<tool_call>", "").replace("</tool_call>", "")

        try:
            # Try to find a JSON object in the string
            string = string.strip()
            if not (string.startswith("{") and string.endswith("}")):
                return None

            parsed_tool_call = json.loads(string)
            if isinstance(parsed_tool_call, dict) and "name" in parsed_tool_call:
                logger.debug(
                    f"{self.name} node found potential tool call in message content: {parsed_tool_call.get('name')}"
                )
                return WorkableToolCall(
                    name=parsed_tool_call.get("name"),
                    args=parsed_tool_call.get("args"),
                    call_id=parsed_tool_call.get("id"),
                )

            return None

        except Exception as e:
            logger.debug(
                f"{self.name} node failed to parse tool call from message: {str(e)}"
            )
            return None
