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
# SPDX-License-Identifier: Apache-2.0
import json
import logging
from typing import Dict, List

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain.chat_models.base import BaseChatModel

from src.graph.environments.planning import PlanningEnvironment
from src.graph.nodes.base_node import BaseNode
from src.graph.prompts import get_thinking_prompt
from src.graph.types import AgentState, BrainState
from src.tools.utils import hydrate_messages, serialize_messages

logger = logging.getLogger(__name__)


class ThinkingNode(BaseNode):
    """Prepares the user-centric thoughts and responses given the brain
    state"""

    def __init__(self):
        self.name = "thinking"

    async def ainvoke(self, state: AgentState, config: Dict = None) -> AgentState:
        logger.info("ThinkingNode invoked")

        if "messages" not in state:
            state["messages"] = []
            logger.debug("Initialized empty messages list in state")

        if not config:
            logger.debug("Config not provided in PlanningNode")
            raise ValueError("Config not provided")

        planning_env = config["configurable"].get("planning_environment")
        if not isinstance(planning_env, PlanningEnvironment):
            logger.error("No planning_environment in configurable")
            return ValueError("Planning environment not initialized")

        llm: BaseChatModel = config.get("configurable", {}).get("llm")

        structured_llm = llm.with_structured_output(BrainState)

        # Add system message first
        local_messages = []
        thinking_prompt = get_thinking_prompt(state["brain"])
        system_message = SystemMessage(content=thinking_prompt)
        local_messages.append(system_message)

        # Hydrate and prune messages
        hydrated = hydrate_messages(state["messages"])
        hydrated = self.prune_messages(hydrated)
        local_messages.extend(hydrated)

        # Add new human message with the task
        human_message = HumanMessage(content=state["task"])
        local_messages.append(human_message)

        # Add the current plan message
        plan_msg = planning_env.get_message_for_current_plan()
        local_messages.append(plan_msg)

        # Get LLM response and structured output
        _response = await structured_llm.ainvoke(local_messages)
        response = BrainState(**_response.dict())
        state["thought"] = response.thought
        state["summary"] = response.summary
        state["brain"] = response

        # Add thinking identity to response
        brain_state_message = AIMessage(
            content=(
                "[Thinking Node] Based on my analysis of the current system state:\n"
                f"Thought: {response.thought}\n"
                f"Summary: {response.summary}"
            )
        )

        # First hydrate any existing messages before serializing
        existing_messages = hydrate_messages(state["messages"])
        global_messages = serialize_messages(existing_messages)
        global_messages.extend(serialize_messages([brain_state_message]))

        # Update the global state with the new messages
        state["messages"] = global_messages
        return state
