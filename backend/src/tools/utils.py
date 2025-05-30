# Copyright 2025 Cisco Systems, Inc. and its affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0"
import asyncio
import datetime
import json
import logging
from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, Dict, List, TypeVar

from browser_use.browser.views import BrowserState
from browser_use.dom.views import DOMElementNode
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from pydantic import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def hydrate_message(message: Dict[str, Any]) -> BaseMessage:
    """
    Hydrate a message dictionary into a LangChain message object.

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
        return AIMessage(
            content=message["content"],
            tool_calls=message.get("tool_calls", []),
            invalid_tool_calls=message.get("invalid_tool_calls", []),
            usage_metadata=message.get("usage_metadata"),
        )
    elif message["type"] == "ToolMessage":
        return ToolMessage(
            content=message["content"],
            tool_call_id=message.get("tool_call_id"),
            tool_name=message.get("tool_name"),
        )
    else:
        return message


def hydrate_messages(messages: List[Dict[str, Any]]) -> List[BaseMessage]:
    """
    Hydrate a list of message dictionaries into LangChain message objects.

    Args:
        messages: List of message dictionaries with 'type' and 'content' fields

    Returns:
        List of LangChain message objects
    """
    return [hydrate_message(m) for m in messages]


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
    elif isinstance(message, AIMessage):
        if hasattr(message, "tool_calls") and message.tool_calls:
            base["tool_calls"] = message.tool_calls
        if hasattr(message, "invalid_tool_calls") and message.invalid_tool_calls:
            base["invalid_tool_calls"] = message.invalid_tool_calls
        if hasattr(message, "usage_metadata") and message.usage_metadata:
            base["usage_metadata"] = message.usage_metadata

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
class ExecutorPromptContext:
    terminal_windows: str
    clickable_elements: str
    browser_tabs: str
    current_date: str
    screenshot: str | None
    current_url: str
    pixels_above: int
    pixels_below: int
    current_page_title: str


def with_retries(num_retries: int = 3, try_timeout: int = 30):
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(num_retries):
                try:
                    return await asyncio.wait_for(
                        func(*args, **kwargs), timeout=try_timeout
                    )
                except asyncio.TimeoutError as e:
                    last_error = e
                    logger.warning(
                        f"Attempt {attempt + 1}/{num_retries} timed out after {try_timeout}s"
                    )
                except Exception as e:
                    last_error = e
                    logger.warning(
                        f"Attempt {attempt + 1}/{num_retries} failed with error: {str(e)}"
                    )

                if attempt < num_retries - 1:
                    await asyncio.sleep(1)  # Add small delay between retries

            raise last_error or Exception("All retry attempts failed")

        return wrapper

    return decorator


@with_retries(num_retries=3, try_timeout=10)
async def get_executor_system_prompt_context(
    config,
) -> ExecutorPromptContext:
    """
    Given the current state of all the systems, generate the prompt which contains the
    sum of all of the context that the agent needs to take action in its environments
    """

    terminal_windows = (
        await config["configurable"].get("terminal_manager").list_terminals()
    )

    browser_context = config["configurable"].get("browser_context")
    if not browser_context:
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

    clickable_elements = await browser_context.get_semantic_elements_string(
        element_tree
    )
    current_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return ExecutorPromptContext(
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


def stringify_dom_element_node(dom_element_node: DOMElementNode) -> str:
    """Convert the DOMElementNode to a string with semantic information"""
    if not dom_element_node:
        return "unknown element"

    # Get basic element information
    tag = dom_element_node.tag_name.lower()
    id = dom_element_node.attributes.get("id", "")
    classes = dom_element_node.attributes.get("class", "")

    # Get text content from children nodes, limited to 50 chars
    text = dom_element_node.get_all_text_till_next_clickable_element()
    if text:
        text = text.strip()[:50]

    # Get specific attributes
    role = dom_element_node.attributes.get(
        "aria-role"
    ) or dom_element_node.attributes.get("role")
    name = dom_element_node.attributes.get("name")
    type = dom_element_node.attributes.get("type")
    placeholder = dom_element_node.attributes.get("placeholder")
    title = dom_element_node.attributes.get("title")
    href = dom_element_node.attributes.get("href")
    value = dom_element_node.attributes.get("value")
    label = dom_element_node.attributes.get(
        "aria-label"
    ) or dom_element_node.attributes.get("label")

    semantic_parts = []

    # Add role or tag
    if role:
        semantic_parts.append(f"{role}")
    else:
        semantic_parts.append(tag)

    if title:
        semantic_parts.append(f"title={title}")

    # Add identifier if present
    if id:
        semantic_parts.append(f"#{id}")

    # Add element-specific information
    if tag == "input":
        if type:
            semantic_parts.append(f'type="{type}"')
        if name:
            semantic_parts.append(f'name="{name}"')
        if placeholder:
            semantic_parts.append(f'placeholder="{placeholder}"')
        if label:
            semantic_parts.append(f'label="{label}"')
        if value:
            semantic_parts.append(f'value="{value}"')
    elif tag == "button":
        if text:
            semantic_parts.append(f'text="{text}"')
    elif tag == "a":
        if text:
            semantic_parts.append(f'text="{text}"')
        if href:
            short_href = href[:30] + "..." if len(href) > 30 else href
            semantic_parts.append(f'href="{short_href}"')
    elif tag == "select":
        if name:
            semantic_parts.append(f'name="{name}"')
        if label:
            semantic_parts.append(f'label="{label}"')
    elif text:
        semantic_parts.append(f'text="{text}"')

    # Add important ARIA attributes
    aria_attributes = [
        "aria-label",
        "aria-description",
        "aria-expanded",
        "aria-selected",
        "aria-checked",
        "aria-pressed",
    ]

    for attr in aria_attributes:
        if value := dom_element_node.attributes.get(attr):
            semantic_parts.append(f'{attr}="{value}"')

    return " ".join(semantic_parts)
