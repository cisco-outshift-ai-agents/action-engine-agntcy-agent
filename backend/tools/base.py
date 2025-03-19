from abc import ABC
from typing import Any, Optional, Callable, Awaitable, TypeVar
from pydantic import BaseModel, Field


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
