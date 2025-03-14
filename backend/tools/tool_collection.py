from typing import Any, Dict, List, Optional, Union

from langchain.tools import BaseTool as LangChainBaseTool
from pydantic import BaseModel

from .base import BaseTool, ToolResult


class ActionEngineToolCollection:
    """Manages a collection of ActionEngine tools with LangChain compatibility"""

    def __init__(
        self, tools: Optional[List[Union[BaseTool, LangChainBaseTool]]] = None
    ):
        self.tools: List[Union[BaseTool, LangChainBaseTool]] = []
        self.tool_map: Dict[str, Union[BaseTool, LangChainBaseTool]] = {}

        # Add any initial tools
        if tools:
            for tool in tools:
                self.add_tool(tool)

    def add_tool(self, tool: Union[BaseTool, LangChainBaseTool]) -> None:
        """Add a tool to the collection"""
        if tool.name in self.tool_map:
            raise ValueError(f"Tool with name {tool.name} already exists")

        self.tools.append(tool)
        self.tool_map[tool.name] = tool

    def remove_tool(self, name: str) -> None:
        """Remove a tool from the collection"""
        if tool := self.tool_map.pop(name, None):
            self.tools.remove(tool)

    def get_tool(self, name: str) -> Optional[Union[BaseTool, LangChainBaseTool]]:
        """Get a tool by name"""
        return self.tool_map.get(name)

    def list_tools(self) -> List[str]:
        """Get list of available tool names"""
        return list(self.tool_map.keys())

    def get_tools(self) -> List[Union[BaseTool, LangChainBaseTool]]:
        """Get tools in format suitable for LLM binding"""
        return self.tools

    async def execute_tool(self, name: str, input_dict: Any) -> ToolResult:
        """Execute a tool by name with given parameters"""
        tool = self.tool_map.get(name)
        if not tool:
            return ToolResult(error=f"Tool {name} not found")

        try:
            # Handle both class-based and decorated tools
            if isinstance(tool, BaseTool):
                result = await tool.ainvoke(input_dict)
            else:
                result = await tool.arun(input_dict)

            # Ensure result is wrapped in ToolResult
            if not isinstance(result, ToolResult):
                result = ToolResult(output=result)

            return result

        except Exception as e:
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
