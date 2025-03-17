import json
import datetime
import logging
from dataclasses import dataclass
from typing import Any, Dict, Type, TypeVar, Union, List
from pydantic import BaseModel
from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    ToolMessage,
    BaseMessage,
    SystemMessage,
)
from graph.types import GraphConfig
from browser_use.browser.views import BrowserState
from src.browser.custom_context import CustomBrowserContext

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def deserialize_message(message: Dict[str, Any]) -> BaseMessage:
    """
    Deserialize a message dictionary into a LangChain message object.

    Args:
        message: Message dictionary with 'type' and 'content' fields

    Returns:
        LangChain message object (HumanMessage, AIMessage, ToolMessage)
    """
    if "type" not in message or "content" not in message:
        raise ValueError("Message dictionary must have 'type' and 'content' fields")

    if message["type"] == "HumanMessage":
        return HumanMessage(content=message["content"])
    elif message["type"] == "SystemMessage":
        return SystemMessage(content=message["content"])
    elif message["type"] == "AIMessage":
        return AIMessage(content=message["content"])
    elif message["type"] == "ToolMessage":
        return ToolMessage(
            content=message["content"],
            tool_call_id=message.get("tool_call_id"),
            tool_name=message.get("tool_name"),
        )
    else:
        return message


def deserialize_messages(messages: List[Dict[str, Any]]) -> List[BaseMessage]:
    """
    Deserialize a list of message dictionaries into LangChain message objects.

    Args:
        messages: List of message dictionaries with 'type' and 'content' fields

    Returns:
        List of LangChain message objects (HumanMessage, AIMessage, ToolMessage)
    """

    return [deserialize_message(m) for m in messages]


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


@dataclass
class EnvironmentPromptContext:
    terminal_windows: str
    clickable_elements: str
    browser_tabs: str
    current_date: str
    screenshot: str | None
    current_url: str
    pixels_above: int
    pixels_below: int
    current_page_title: str


async def get_environment_system_prompt_context(
    config: GraphConfig,
) -> EnvironmentPromptContext:
    """
    Given the current state of all the systems, generate the prompt which contains the
    sum of all of the context that the agent needs to take action in its environments
    """

    terminal_windows = (
        await config["configurable"].get("terminal_manager").list_terminals()
    )

    browser_context: CustomBrowserContext = config["configurable"].get(
        "browser_context"
    )
    if not isinstance(browser_context, CustomBrowserContext):
        logger.info(f"Browser context: {browser_context}")
        raise TypeError("Browser context is not an instance of CustomBrowserContext")

    browser_state: BrowserState = await browser_context.get_state(use_vision=True)
    if not isinstance(browser_state, BrowserState):
        logger.info(f"Browser state: {browser_state}")
        raise TypeError("Browser state is not an instance of BrowserState")

    element_tree = browser_state.element_tree
    screenshot = browser_state.screenshot
    browser_tabs = browser_state.tabs
    pixels_above = browser_state.pixels_above
    pixels_below = browser_state.pixels_below
    current_url = browser_state.url
    current_page_title = browser_state.title

    clickable_elements = element_tree.clickable_elements_to_string()
    current_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return EnvironmentPromptContext(
        terminal_windows=json.dumps(terminal_windows),
        clickable_elements=str(clickable_elements),
        browser_tabs=str(browser_tabs),
        current_date=current_date,
        screenshot=screenshot,
        current_url=current_url,
        pixels_above=pixels_above,
        pixels_below=pixels_below,
        current_page_title=current_page_title,
    )
