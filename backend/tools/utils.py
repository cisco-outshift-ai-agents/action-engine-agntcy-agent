import json
from typing import Any, Dict, Type, TypeVar, Union, List
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

T = TypeVar("T", bound=BaseModel)


def deserialize_messages(messages: List[Dict[str, Any]]) -> List[Any]:
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
