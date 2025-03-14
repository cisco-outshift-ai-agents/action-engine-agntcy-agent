from abc import ABC
from typing import Any, Dict, Optional, Type, Union, Callable, Awaitable, TypeVar, cast
from functools import wraps
from inspect import signature

from langchain.tools import Tool, BaseTool as LangChainBaseTool
from pydantic import BaseModel, Field, create_model


class ToolResult(BaseModel):
    """Standard result format for all tools"""

    output: Any = Field(default=None, description="The tool's output")
    error: Optional[str] = Field(
        default=None, description="Error message if the tool failed"
    )
    system: Optional[str] = Field(default=None, description="System-level messages")

    def __bool__(self) -> bool:
        """Allow boolean checking of results"""
        return self.error is None and self.output is not None

    def __str__(self) -> str:
        """String representation prioritizing error messages"""
        return str(self.error) if self.error else str(self.output)


T = TypeVar("T", bound=Callable[..., Awaitable[Any]])


def actionengine_tool(
    name: str, description: str, parameters: Dict = None
) -> Callable[[T], Tool]:
    """Decorator that creates a LangChain tool with ActionEngine patterns"""

    def decorator(func: T) -> Tool:
        # Create args schema if parameters provided
        args_schema = None
        if parameters:
            fields = {
                "input": (
                    dict if parameters["type"] == "object" else str,
                    Field(description=description),
                )
            }

            args_schema = create_model(
                f"{name}Args",
                **fields,
                __config__=type("Config", (), {"extra": "forbid"}),
            )

        @wraps(func)
        async def async_wrapped(input_dict: Union[str, dict]) -> str:
            """Async wrapper that handles ToolResult conversion"""
            try:
                result = await func(input_dict)
                if isinstance(result, ToolResult):
                    return str(result)
                return str(ToolResult(output=result))
            except Exception as e:
                return str(ToolResult(error=str(e)))

        # Create tool with proper async handling
        tool = Tool(
            name=name,
            description=description,
            func=lambda **kwargs: "This tool only supports async execution",
            coroutine=async_wrapped,
            args_schema=args_schema,
            return_direct=True,
        )

        return tool

    return decorator


class BaseTool(LangChainBaseTool):
    """Base class for all tools, integrating with LangChain patterns"""

    name: str
    description: str = ""
    parameters: Dict = Field(default_factory=dict)

    async def _arun(self, *args: Any, **kwargs: Any) -> str:
        """Async execution with standardized error handling"""
        try:
            result = await self.execute(*args, **kwargs)
            if isinstance(result, ToolResult):
                return str(result)
            return str(ToolResult(output=result))
        except Exception as e:
            return str(ToolResult(error=str(e)))

    def _run(self, *args: Any, **kwargs: Any) -> str:
        """Sync execution is not supported"""
        raise NotImplementedError("This tool only supports async execution")

    async def execute(self, *args: Any, **kwargs: Any) -> Any:
        """Main execution method to be implemented by subclasses"""
        raise NotImplementedError()
