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
"""Generate ACP manifest for graph-runner agent."""

from pathlib import Path
from typing import Dict, Any

from agntcy_acp.manifest import (
    AgentManifest,
    AgentMetadata,
    AgentACPSpec,
    Capabilities,
    AgentRef,
)

from .models import (
    AgentInput,
    AgentOutput,
    Config,
    TERMINAL_APPROVAL_INTERRUPT,
)


def clean_pydantic_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    """Clean Pydantic schema for ACP manifest by removing metadata fields."""
    clean_schema = schema.copy()
    metadata_fields = ["$schema", "$defs", "title"]
    for field in metadata_fields:
        clean_schema.pop(field, None)
    return clean_schema


def add_schema_defs(
    schema: Dict[str, Any], full_schema: Dict[str, Any]
) -> Dict[str, Any]:
    """Adds $defs from full schema into the target schema."""
    if "$defs" in full_schema:
        schema["$defs"] = full_schema["$defs"]
    return schema


def create_agent_manifest() -> AgentManifest:
    """Create the agent manifest with proper schemas and capabilities."""
    # Get full schemas to preserve definitions
    config_schema = Config.model_json_schema()

    # Clean metadata from schemas
    input_schema = clean_pydantic_schema(AgentInput.model_json_schema())
    output_schema = clean_pydantic_schema(AgentOutput.model_json_schema())
    clean_config_schema = clean_pydantic_schema(config_schema)

    # Add definitions back to config schema
    config_with_defs = add_schema_defs(clean_config_schema, config_schema)

    description = """
# ActionEngine Browser Agent

## Overview
ActionEngine is a user/agent collaborative playground designed to assist network engineers by enabling direct interaction with Cisco products, SaaS services, web browsers, terminal environments, and code editors.

## Core Capabilities
- **Collaborative Environment**: Users and agents work in tandem towards achieving goals
- **Learning from Observation**: Ability to learn from user behavior to autonomously execute complex workflows
- **Cross-Environment Operation**: Seamlessly works across browsers, terminals, and various network tools
- **Vision and UI Understanding**: Uses advanced vision capabilities to interpret and interact with interfaces
- **Session Management**: Maintains browser sessions and context between operations
- **Adaptive Decision Making**: Autonomously handles UI changes and unexpected situations

## Trust and Transparency
ActionEngine builds trust through:
- Interactive validation of agent behavior
- Human-in-the-loop interventions when needed
- Clear presentation of planned actions
- Real-time error detection and resolution

## PurpleBadge Integration
As a core component of the PurpleBadge project, this agent comes pre-trained with networking-specific capabilities while remaining flexible enough to learn new workflows through observation.

## Example Use Cases
- Certificate management across multiple systems
- Cross-platform automation tasks
- Network configuration workflows
- System monitoring and maintenance
- Enterprise tool integration

The agent serves as a bridge between traditional applications and the emerging Internet of Agents, enabling agentic behavior in systems not originally designed for it.
    """.strip()

    return AgentManifest(
        metadata=AgentMetadata(
            ref=AgentRef(name="ActionEngine Browser Agent", version="1.0.0"),
            description=description,
        ),
        specs=AgentACPSpec(
            input=input_schema,
            output=output_schema,
            config=config_with_defs,
            capabilities=Capabilities(threads=True, interrupts=True),
            custom_streaming_update=None,
            thread_state=None,
            interrupts=[TERMINAL_APPROVAL_INTERRUPT],
        ),
    )


# Create manifest instance at module level
manifest = create_agent_manifest()

if __name__ == "__main__":
    output_path = Path(__file__).parent.parent / "manifest.json"
    with open(output_path, "w") as f:
        f.write(
            manifest.model_dump_json(exclude_unset=True, exclude_none=True, indent=2)
        )
