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
from abc import ABC
from typing import Any, Awaitable, Callable, Optional, TypeVar

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
