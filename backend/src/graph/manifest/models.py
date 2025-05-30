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
"""Models for manifest generation."""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from agntcy_acp.manifest import Interrupt


class BrowserConfig(BaseModel):
    """Browser environment configuration."""

    use_own_browser: bool = Field(
        default=False, description="Whether to use an existing browser instance"
    )
    keep_browser_open: bool = Field(
        default=True, description="Whether to keep the browser open between runs"
    )
    headless: bool = Field(
        default=True, description="Whether to run browser in headless mode"
    )
    disable_security: bool = Field(
        default=False, description="Whether to disable browser security features"
    )
    window_w: int = Field(default=1920, description="Browser window width")
    window_h: int = Field(default=1080, description="Browser window height")


class ExecutionConfig(BaseModel):
    """Task execution configuration."""

    max_steps: int = Field(
        default=100, description="Maximum number of steps to execute"
    )
    max_actions_per_step: int = Field(
        default=10, description="Maximum number of actions per step"
    )
    tool_calling_method: str = Field(
        default="auto", description="Method to use for tool calling"
    )


class VisionConfig(BaseModel):
    """Vision capabilities configuration."""

    enabled: bool = Field(
        default=False, description="Whether to use vision capabilities"
    )
    max_images_per_call: Optional[int] = Field(
        default=None, description="Limit on number of images per LLM call"
    )


class Config(BaseModel):
    """Full agent configuration."""

    browser: BrowserConfig
    execution: ExecutionConfig
    vision: VisionConfig


class AgentInput(BaseModel):
    """Input format for agent tasks."""

    task: str = Field(description="The task to execute")
    add_infos: Optional[str] = Field(
        default=None, description="Additional information for task execution"
    )


# TODO: (julvalen) Ensure this syncs up with the AgentState TypedDict in /src/graph/types.py
# I don't know how to resolve the necessity between the Annotations in the TypedDict
# and the need for AgentOutput to be a Pydantic model.
class AgentOutput(BaseModel):
    """Pydantic model matching AgentState structure"""

    # Core state
    task: Optional[str] = Field(default=None, description="The task to execute")
    plan: Optional[Dict[str, Any]] = Field(
        default=None, description="Current plan state"
    )

    # Brain state
    brain: Optional[Dict[str, Any]] = Field(
        default=None, description="Brain state tracking"
    )
    thought: Optional[str] = Field(
        default=None, description="Current reasoning process"
    )
    summary: Optional[str] = Field(
        default=None, description="Brief summary of current state and progress"
    )
    context: Optional[Dict[str, Any]] = Field(
        default=None, description="Context information"
    )

    # Memory and history
    messages: Optional[List[Dict]] = Field(default=None, description="Message history")
    tools_used: Optional[List[Dict]] = Field(
        default=None, description="History of used tools"
    )

    # Control flow
    error: Optional[str] = Field(default=None, description="Error message if any")
    next_node: Optional[str] = Field(default=None, description="Next node to execute")
    exiting: Optional[bool] = Field(
        default=None, description="Whether execution is complete"
    )

    # Tool approval management
    tool_calls: Optional[List[Dict]] = Field(
        default=None, description="Pending tool calls"
    )
    pending_approval: Optional[Dict[str, Any]] = Field(
        default=None, description="Tool calls pending approval"
    )

    class Config:
        """Pydantic configuration"""

        extra = "allow"


class TerminalApprovalOutput(BaseModel):
    """Schema for terminal command approval interrupt data."""

    tool_call: Dict[str, Any] = Field(description="The tool call requiring approval")
    message: str = Field(description="Message to display to the user")


class TerminalApprovalInput(BaseModel):
    """Schema for terminal command approval response."""

    approved: bool = Field(description="Whether the command is approved for execution")
    reason: Optional[str] = Field(
        default=None, description="Optional reason for rejection"
    )


# Predefined interrupt type with proper schemas
TERMINAL_APPROVAL_INTERRUPT = Interrupt(
    interrupt_type="terminal_approval",
    description="Request approval for terminal command execution",
    interrupt_payload=TerminalApprovalOutput.model_json_schema(),
    resume_payload=TerminalApprovalInput.model_json_schema(),
)
