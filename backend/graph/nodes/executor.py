import logging
from typing import Dict, List, Any
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, BaseMessage
from langchain_openai import ChatOpenAI

from core.types import AgentState
from tools.tool_collection import ActionEngineToolCollection
from tools.terminal import terminal_tool
from tools.file_saver import file_saver_tool
from tools.browser_use import browser_use_tool
from tools.google_search import google_search_tool
from tools.python_execute import python_execute_tool
from tools.str_replace_editor import str_replace_editor_tool
from tools.terminate import terminate_tool

logger = logging.getLogger(__name__)


class ExecutorNode:
    """Executes tools in a LangGraph workflow"""

    def __init__(self):
        self.name = "executor"
        self.tool_collection = ActionEngineToolCollection(
            [
                terminal_tool,
                file_saver_tool,
                browser_use_tool,
                google_search_tool,
                python_execute_tool,
                str_replace_editor_tool,
                terminate_tool,
            ]
        )

    async def __call__(self, state: AgentState, config: Dict):
        """Make node callable for LangGraph and ensure async execution"""
        return await self.ainvoke(state, config)

    def _serialize_message(self, message: BaseMessage) -> Dict[str, Any]:
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

    async def ainvoke(self, state: AgentState, config: Dict) -> Dict:
        """Async invocation with direct tool execution"""
        if "messages" not in state:
            state["messages"] = []
            logger.debug("Initialized empty messages list in state")

        llm: ChatOpenAI = config.get("configurable", {}).get("llm")
        if not llm:
            raise ValueError("LLM not provided in config")

        # Bind tools to LLM
        bound_llm = llm.bind_tools(self.tool_collection.get_tools())

        # Deserialize messages for LLM
        messages = [
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
            for m in state["messages"]
        ]

        # Add new human message
        human_message = HumanMessage(content=state["task"])
        messages.append(human_message)

        # Get LLM response with tool calls
        response: AIMessage = await bound_llm.ainvoke(messages)

        logger.info(f"Response from LLM: {response}")

        # Serialize messages for state storage
        serialized_messages = [self._serialize_message(m) for m in messages]
        serialized_messages.append(self._serialize_message(response))

        # Execute any tool calls
        if hasattr(response, "tool_calls") and response.tool_calls:
            tool_messages = await self.execute_tools(response)
            serialized_messages.extend(
                [self._serialize_message(tm) for tm in tool_messages]
            )

        state["messages"] = serialized_messages
        return state

    async def execute_tools(self, message: AIMessage) -> List[ToolMessage]:
        """Execute tools using tool collection"""
        tool_messages = []

        for tool_call in message.tool_calls:
            try:
                name = tool_call["name"]
                args = tool_call["args"]

                if not name:
                    raise ValueError("Tool call missing function")

                result = await self.tool_collection.execute_tool(name, args)
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
                tool_messages.append(
                    ToolMessage(
                        tool_name=tool_call.function.name,
                        content=str(e),
                        tool_call_id=tool_call.id,
                    )
                )

        return tool_messages
