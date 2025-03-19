import logging
from typing import Any, Dict, List, Optional

from langchain.tools import BaseTool
from langchain_core.messages import AIMessage
from .base import ToolResult
from graph.types import WorkableToolCall

logger = logging.getLogger(__name__)


class ActionEngineToolCollection:
    """Manages a collection of ActionEngine tools with LangChain compatibility"""

    def __init__(self, tools: Optional[List[BaseTool]] = None):
        self.tools: List[BaseTool] = []
        self.tool_map: Dict[str, BaseTool] = {}

        # Add any initial tools
        if tools:
            for tool in tools:
                self.add_tool(tool)

    def add_tool(self, tool: BaseTool) -> None:
        """Add a tool to the collection"""
        if tool.name in self.tool_map:
            raise ValueError(f"Tool with name {tool.name} already exists")

        self.tools.append(tool)
        self.tool_map[tool.name] = tool

    def remove_tool(self, name: str) -> None:
        """Remove a tool from the collection"""
        if tool := self.tool_map.pop(name, None):
            self.tools.remove(tool)

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name"""
        return self.tool_map.get(name)

    def list_tools(self) -> List[str]:
        """Get list of available tool names"""
        return list(self.tool_map.keys())

    def get_tools(self) -> List[BaseTool]:
        """Get tools in format suitable for LLM binding"""
        return self.tools

    async def execute_tool(
        self, name: str, input_dict: Any, config: Dict = None
    ) -> ToolResult:
        """Execute a tool by name with given parameters"""
        tool = self.tool_map.get(name)

        logger.info(f"Executing tool {name} with input: {input_dict}")

        if not tool:
            return ToolResult(error=f"Tool {name} not found")

        try:
            # Let LangChain handle config injection via type hints
            result = await tool.ainvoke(input_dict, config=config)
            return (
                result if isinstance(result, ToolResult) else ToolResult(output=result)
            )

        except Exception as e:
            logger.error(f"Failed to execute {name}: {str(e)}")
            return ToolResult(error=str(e), system=f"Failed to execute {name}")

    def get_schemas(self) -> List[Dict]:
        """Get OpenAI function schemas for all tools"""
        schemas = []
        for tool in self.tools:
            if isinstance(tool, BaseTool):
                schemas.append(
                    {
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": tool.parameters,
                        },
                    }
                )
            else:
                # Handle LangChain tools
                schemas.append(tool.metadata)
        return schemas

    def validate_workable_tool_calls(self, tool_calls: List[WorkableToolCall]) -> bool:
        """Validate tool calls against available tools"""

        for tool_call in tool_calls:
            if tool_call.name not in self.tool_map:
                return False
        return True
