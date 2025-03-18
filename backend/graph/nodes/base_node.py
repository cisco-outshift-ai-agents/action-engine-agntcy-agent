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
        logger.info(f"Executing tools from message: {message}")

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

                logger.info(f"Executing tool {name} with args: {args}")

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
        Given the full sum of messages from the internal store,
        prune out the irrelevant information and return only the pertinent
        information.
        """
        beginning_length = len(messages)

        # Prune out system messages
        pruned_messages = [
            msg for msg in messages if not isinstance(msg, SystemMessage)
        ]

        # Prune out human messages
        pruned_messages = [msg for msg in messages if not isinstance(msg, HumanMessage)]

        # Prune out empty messages
        pruned_messages = [msg for msg in pruned_messages if msg.content]

        # Prune out tool messages and convert them to AI messages -- if we don't do this, (I think) the hermes parser for vLLM freaks out and
        # refuses to show new tool calls
        pruned_messages = [
            AIMessage(content=msg.content) if isinstance(msg, ToolMessage) else msg
            for msg in pruned_messages
        ]

        # Keep only the last 15 messages
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

        if not self.tool_collection:
            response: AIMessage = await llm.ainvoke(messages)
            return response

        MAX_ATTEMPTS = 3
        attempt = 0

        while attempt < MAX_ATTEMPTS:
            if attempt > 0:
                logger.info(f"Retrying model call with tool calls, attempt {attempt}")
                messages.append(AIMessage(content=get_tool_call_retry_prompt()))

            attempt += 1
            try:
                response: AIMessage = await llm.ainvoke(messages)
                workable_tool_calls = self.get_workable_tool_calls(response)
                if len(
                    workable_tool_calls
                ) > 0 and self.tool_collection.validate_workable_tool_calls(
                    workable_tool_calls
                ):
                    return response
            except Exception as e:
                logger.error(f"Error calling model with tool calls: {str(e)}")
                continue

        return None

    def get_workable_tool_calls(self, message: AIMessage) -> List[WorkableToolCall]:
        """
        Convert tool calls to workable format, parsing out the necessary information
        regardless of whether the tool call is a dictionary or object.
        """
        tool_calls: List[WorkableToolCall] = []

        for tool_call in message.tool_calls:
            if isinstance(tool_call, dict):
                tool_calls.append(
                    WorkableToolCall(
                        name=tool_call.get("name")
                        or tool_call.get("function", {}).get("name"),
                        args=tool_call.get("args")
                        or tool_call.get("function", {}).get("arguments"),
                        call_id=tool_call.get("id"),
                    )
                )
            else:
                tool_calls.append(
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

        extracted_text_tool_call = self.extract_workable_tool_call_from_vllm_string(
            message.content
        )
        if extracted_text_tool_call:
            tool_calls.append(
                WorkableToolCall(
                    name=extracted_text_tool_call.name,
                    args=extracted_text_tool_call.args,
                    call_id=extracted_text_tool_call.id,
                )
            )

        return tool_calls

    # Sometimes the tool call appears within the message itself
    # I think this is probably a bug with vLLM and the hermes parser
    # but we can handle it here while we wait for a fix
    def extract_workable_tool_call_from_vllm_string(
        self, string: str
    ) -> Optional[WorkableToolCall]:
        """
        Extract a tool call from a vLLM string
        """

        # Remove <tool_call> tags
        string = string.replace("<tool_call>", "").replace("</tool_call>", "")

        try:
            parsed_tool_call = json.loads(string)
            return WorkableToolCall(
                name=parsed_tool_call.get("name"),
                args=parsed_tool_call.get("args"),
                call_id=parsed_tool_call.get("id"),
            )
        except Exception as e:
            logger.error(f"Error parsing tool call from message: {str(e)}")
            return None
