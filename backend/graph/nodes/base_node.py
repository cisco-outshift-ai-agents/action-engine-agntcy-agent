import logging
from typing import Dict, List
from langchain_core.messages import (
    AIMessage,
    ToolMessage,
    SystemMessage,
    BaseMessage,
    HumanMessage,
)
from graph.types import AgentState

logger = logging.getLogger(__name__)


class BaseNode:
    """Base class for all agent nodes"""

    name: str = "base"  # Default name, will be overridden by child classes

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

        for tool_call in message.tool_calls:
            try:
                name = tool_call["name"]
                args = tool_call["args"]

                if not name:
                    raise ValueError("Tool call missing function")

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
                random_id = str(hash(str(tool_call) + str(result)))[:8]
                tool_messages.append(
                    ToolMessage(
                        tool_name=tool_call["name"],
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
        # Prune out system messages
        pruned_messages = [
            msg for msg in messages if not isinstance(msg, SystemMessage)
        ]

        # Prune out human messages
        pruned_messages = [msg for msg in messages if not isinstance(msg, HumanMessage)]

        # Prune out empty messages
        pruned_messages = [msg for msg in pruned_messages if msg.content]

        # Keep only the last 15 messages
        pruned_messages = pruned_messages[-15:]

        return pruned_messages
