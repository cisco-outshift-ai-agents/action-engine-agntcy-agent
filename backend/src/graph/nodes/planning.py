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
import logging
from typing import Dict, List

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, BaseMessage
from langchain.chat_models.base import BaseChatModel

from src.graph.environments.planning import PlanningEnvironment
from src.graph.nodes.base_node import BaseNode
from src.graph.prompts import get_planner_prompt, get_hints_prompt
from src.graph.types import AgentState
from src.tools.planning import planning_tool
from src.tools.terminate import terminate_tool
from src.tools.tool_collection import ActionEngineToolCollection
from src.tools.utils import hydrate_messages, serialize_messages
from src.semantic_routing_induction.semantic_router_utils import (
    get_hints_for_query_with_loaded_routers,
)

logger = logging.getLogger(__name__)


class PlanningNode(BaseNode):
    """Provides high-level guidance but doesn't control execution flow"""

    def __init__(self):
        self.name = "planning"
        self.tool_collection = ActionEngineToolCollection([planning_tool])
        self.planner_prompt = get_planner_prompt()
        self.hints_prompt = get_hints_prompt()

    async def ainvoke(self, state: AgentState, config: Dict = None) -> AgentState:
        logger.info("PlanningNode invoked")
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

        bound_llm = llm.bind_tools(
            self.tool_collection.get_tools(),
            tool_choice="planning",
            parallel_tool_calls=False,
        ).with_config(config=config)

        # Add hints to the planner
        if config["configurable"]["default_config"]["enable_workflow_memory"]:
            domain, subdomain, website, hints = get_hints_for_query_with_loaded_routers(
                state["task"],
                config["configurable"]["default_config"]["routers"][0],
                config["configurable"]["default_config"]["routers"][1],
                config["configurable"]["default_config"]["workflow_files"],
                ext=".txt",
            )
            logger.info(f"Retrieved hints: {hints}")

            if hints is not None:
                self.planner_prompt += f"\n\n{self.hints_prompt}:\n{hints}"

        # Add system message first
        local_messages = []
        system_message = SystemMessage(content=self.planner_prompt)
        local_messages.append(system_message)

        # Hydrate existing messages
        hydrated = hydrate_messages(state["messages"])
        hydrated = self.prune_messages(hydrated)
        local_messages.extend(hydrated)

        # Add new human message with the task
        human_message = HumanMessage(content=state["task"])
        local_messages.append(human_message)

        # Add the current plan message
        plan_msg = planning_env.get_message_for_current_plan()
        if plan_msg.content != "No plan available":
            local_messages.append(plan_msg)

        # Get LLM response with tool calls
        raw_response: AIMessage = await self.call_model_with_tool(
            llm=bound_llm, messages=local_messages
        )
        if not raw_response:
            raise ValueError("LLM response not provided")

        # Add planner identity to response
        prefixed_content = f"[Planning Node] Based on the current state, I am updating the plan:\n{raw_response.content}"
        response = AIMessage(
            content=prefixed_content,
            tool_calls=(
                raw_response.tool_calls if hasattr(raw_response, "tool_calls") else None
            ),
        )

        # First hydrate any existing messages before serializing
        existing_messages = hydrate_messages(state["messages"])
        global_messages = serialize_messages(existing_messages)
        global_messages.extend(serialize_messages([response]))

        # Execute any tool calls and add the tool messages to the global state
        if hasattr(raw_response, "tool_calls") and raw_response.tool_calls:
            logger.info(f"Executing tool calls: {response.tool_calls}")
            tool_messages = await self.execute_tools(message=response, config=config)
            global_messages.extend(serialize_messages(tool_messages))

        # Update plan in state if available
        plan = planning_env.get_plan()
        if plan:
            state["plan"] = plan.to_dict()
        else:
            state["plan"] = None

        # Update the global state with the new messages
        state["messages"] = global_messages
        return state
