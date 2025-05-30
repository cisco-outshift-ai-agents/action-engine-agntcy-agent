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
import logging
from enum import Enum
from typing import Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from .base import ToolResult

logger = logging.getLogger(__name__)


class TerminationStatus(str, Enum):
    """Available termination statuses"""

    SUCCESS = "success"
    FAILURE = "failure"


class TerminateInput(BaseModel):
    """Input model for termination"""

    status: TerminationStatus = Field(description="The completion status")
    reason: Optional[str] = Field(None, description="Explanation for termination")


@tool("terminate", args_schema=TerminateInput)
async def terminate_tool(
    status: TerminationStatus,
    reason: Optional[str] = None,
) -> ToolResult:
    """
    Signal that an interaction flow should terminate. Used in two scenarios:
    1. SUCCESS: The requested task has been completed successfully
    2. FAILURE: The task cannot be completed due to errors or limitations

    Examples:
        Success termination:
        ```python
        {
            "status": "success",
            "reason": "Successfully created new user profile"
        }
        ```

        Failure termination:
        ```python
        {
            "status": "failure",
            "reason": "Required file not found: config.json"
        }
        ```

    Args:
        status: Must be either "success" or "failure"
        reason: Required explanation for why the flow is terminating
    """
    logger.info(f"Terminate tool called with status: {status}, reason: {reason}")

    if not isinstance(status, TerminationStatus):
        return ToolResult(
            error=f"Invalid status. Must be one of: {[s.value for s in TerminationStatus]}"
        )

    if not reason:
        return ToolResult(
            error="Reason is required - must explain why the flow is terminating"
        )

    message = f"Flow terminated - {status.upper()}\nReason: {reason}"
    system_message = f"status={status},reason={reason}"
    return ToolResult(output=message, system=system_message)
