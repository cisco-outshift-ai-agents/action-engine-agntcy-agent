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
from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict
from enum import Enum


class Operation(BaseModel):
    """Represents a single operation performed by the user"""

    original_op: str
    target: str
    value: Optional[str] = None
    op: str


class LTOEvent(BaseModel):
    """Represents an event in the learning through observation process"""

    website: str
    session_id: str
    operation: Operation
    timestamp: Optional[str] = None
    action_uid: str
    domain: str
    subdomain: str
    raw_html: str


class AnalyzedLTOResult(BaseModel):
    """Represents the result of analyzing a sequence of LTOEvents"""

    session_id: str
    workflow: str
    actions: List[str]


class StepStatus(str, Enum):
    not_started = "not_started"
    in_progress = "in_progress"
    completed = "completed"
    blocked = "blocked"


class SubStep(BaseModel):
    """Represents a substep in a plan step"""

    content: str
    notes: Optional[str] = None
    status: StepStatus = StepStatus.not_started


class Step(BaseModel):
    """Represents a step in a plan"""

    content: str
    notes: Optional[str] = None
    status: StepStatus = StepStatus.not_started
    substeps: List[SubStep] = []


class Plan(BaseModel):
    """Represents a structured plan"""

    plan_id: Optional[str] = None
    steps: List[Step]


class LTOResponse(BaseModel):
    """The response of the learning observation chain"""

    browser_behavior_summary: str = Field(
        ...,
        description="The summary of the previous few actions that the user performed",
    )
    workflow_summary: str = Field(
        ...,
        description="The summary of how these actions fit into the overall workflow.",
    )
    plan: Optional[Plan] = Field(
        None,
        description="The structured plan generated from the workflow",
    )
