import json
import datetime
from typing import Any, Dict, Type, TypeVar, Union, List
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, BaseMessage
from core.types import AgentConfig

T = TypeVar("T", bound=BaseModel)


def deserialize_messages(messages: List[Dict[str, Any]]) -> List[BaseMessage]:
    """
    Deserialize a list of message dictionaries into LangChain message objects.

    Args:
        messages: List of message dictionaries with 'type' and 'content' fields

    Returns:
        List of LangChain message objects (HumanMessage, AIMessage, ToolMessage)
    """
    return [
        (
            HumanMessage(content=m["content"])
            if m["type"] == "HumanMessage"
            else (
                AIMessage(content=m["content"])
                if m["type"] == "AIMessage"
                else (
                    ToolMessage(
                        content=m["content"],
                        tool_call_id=m.get("tool_call_id"),
                        tool_name=m.get("tool_name"),
                    )
                    if m["type"] == "ToolMessage"
                    else m
                )
            )
        )
        for m in messages
    ]


def serialize_message(message: BaseMessage) -> Dict[str, Any]:
    """Convert a message to a serializable format"""
    base = {
        "type": message.__class__.__name__,
        "content": message.content,
    }
    # Handle additional fields for specific message types
    if isinstance(message, ToolMessage):
        base.update(
            {
                "tool_call_id": message.tool_call_id,
                "tool_name": message.tool_name,
            }
        )
    return base


def serialize_messages(messages: List[BaseMessage]) -> List[Dict[str, Any]]:
    """
    Serialize a list of LangChain message objects into dictionaries.

    Args:
        messages: List of LangChain message objects (HumanMessage, AIMessage, ToolMessage)

    Returns:
        List of serialized message dictionaries
    """
    return [serialize_message(m) for m in messages]


async def get_environment_system_prompt_context(config: AgentConfig):
    """
    Given the current state of all the systems, generate the prompt which contains the
    sum of all of the context that the agent needs to take action in its environments
    """

    terminal_windows = await config.configurable.terminal_manager.list_terminals()
    browser_state = await config.configurable.browser_context.get_state(use_vision=True)
    element_tree = browser_state.element_tree
    clickable_elements = element_tree.clickable_elements_to_string()
    browser_tabs = browser_state.tabs
    current_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return {terminal_windows, clickable_elements, browser_tabs, current_date}
