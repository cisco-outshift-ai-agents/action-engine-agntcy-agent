import json
import logging
from typing import Dict, List, Optional, Any
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, Graph, START, END
from langgraph.channels.last_value import LastValue
from langchain_core.messages import (
    HumanMessage,
    SystemMessage,
    AIMessage,
    FunctionMessage,
)
from langchain_core.prompts import ChatPromptTemplate
from langgraph.types import Command

from core.types import EnvironmentType, BrainState, EnvironmentOutput, AgentState
from browser_use.agent.views import ActionModel, ActionResult, AgentOutput
from browser_use.agent.prompts import AgentMessagePrompt, SystemPrompt
from browser_use.controller.service import Controller

logger = logging.getLogger(__name__)


class BrainState(BaseModel):
    """Captures the thought process and state evaluation"""

    prev_action_evaluation: str = ""
    important_contents: str = ""
    task_progress: str = ""
    future_plans: str = ""
    thought: str = ""
    summary: str = ""


class EnvironmentOutput(BaseModel):
    """Standardized output from environment execution"""

    success: bool
    next_env: Optional[str] = None
    result: Dict = {}
    error: Optional[str] = None


class TaskAnalysis(BaseModel):
    """Simple environment selection model"""

    primary_environment: str = Field(
        description="The main environment to use (browser/terminal/code)",
        pattern="^(browser|terminal|code)$",
    )
    reasoning: str = Field(description="Why this environment was chosen")
    required_tools: List[str] = Field(default_factory=list)


async def analyze_task(state: AgentState, llm) -> TaskAnalysis:
    """Analyze task and determine appropriate environment"""
    structured_llm = llm.with_structured_output(TaskAnalysis)

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """You are an expert at breaking down tasks and determining the best environment to execute them.
Available environments:
- browser: For web automation, form filling, navigation
- terminal: For file system operations, running commands
- code: For code writing, editing, and execution
""",
            ),
            ("user", "Task: {task}"),
        ]
    )

    # Use proper variable substitution
    messages = prompt.format_messages(task=state["task"])
    response = await structured_llm.ainvoke(messages)
    return response


class RouterNode:
    """Routes to appropriate environment based on task analysis"""

    def __init__(self):
        self.name = "router"

    async def __call__(self, state: AgentState, config: Dict):
        """Make node callable for LangGraph and ensure async execution"""
        return await self.ainvoke(state, config)

    def invoke(self, state: AgentState, config: Dict):
        """Prevent sync execution"""
        raise NotImplementedError("Router requires async execution")

    async def ainvoke(self, state: AgentState, config: Dict) -> Dict:
        """Async invocation"""
        logger.debug(f"Config received in router: {config}")
        logger.debug(f"Configurable section: {config.get('configurable', {})}")

        llm = config.get("configurable", {}).get("llm")
        if not llm:
            logger.error("Missing LLM in config:")
            logger.error(f"Full config: {config}")
            raise ValueError("LLM not provided in config")

        if not state.get("task_analysis"):
            analysis = await analyze_task(state, llm)
            state["task_analysis"] = analysis.model_dump()

        # Update the current environment in state
        next_env = state["task_analysis"]["primary_environment"] + "_env"
        state["current_env"] = next_env

        return Command(goto=next_env)


class ChainOfThoughtNode:
    """Provides high-level guidance but doesn't control execution flow"""

    def __init__(self):
        self.name = "chain_of_thought"

    async def __call__(self, state: AgentState, config: Dict):
        """Make node callable for LangGraph and ensure async execution"""
        return await self.ainvoke(state, config)

    def invoke(self, state: AgentState, config: Dict):
        """Prevent sync execution"""
        raise NotImplementedError("Chain of thought requires async execution")

    async def ainvoke(self, state: AgentState, config: Dict) -> AgentState:
        """Think about current state and provide guidance"""
        llm = config.get("configurable", {}).get("llm")
        if not llm:
            raise ValueError("LLM not provided in config")

        messages = [
            HumanMessage(content=state["task"]),
            SystemMessage(
                content="Think about how to accomplish this task. What tools or approaches might help?"
            ),
        ]

        response = await llm.ainvoke(messages)

        # Update brain state with thoughts but don't control flow
        state["brain"] = BrainState(
            thought=response.content,
            summary=_generate_summary(state),
        ).model_dump()

        return state


class BrowserEnvNode:
    """Handles browser environment execution with agent-like behavior"""

    def __init__(self):
        self.name = "browser_env"
        self.controller = Controller()
        self.message_manager = None  # Will initialize in ainvoke

    async def __call__(self, state: AgentState, config: Dict):
        """Make node callable for LangGraph and ensure async execution"""
        return await self.ainvoke(state, config)

    async def ainvoke(self, state: AgentState, config: Dict) -> Dict:
        """Execute browser actions using agent-like planning"""
        llm = config.get("configurable", {}).get("llm")
        env_registry = config.get("configurable", {}).get("env_registry", {})
        browser_env = env_registry.get(EnvironmentType.BROWSER)

        if not browser_env or not llm:
            return {"error": "Missing required components"}

        try:
            # Get current browser state
            browser_state = await browser_env.browser_context.get_state(use_vision=True)

            # Get next actions using LLM
            messages = self._prepare_messages(state, browser_state)
            tools = browser_env.tool_registry.get_openai_functions()

            # LLM planning phase
            ai_message = await llm.ainvoke(messages, functions=tools)
            parsed_actions = self._parse_llm_response(ai_message)

            # Execute actions
            results = await self.controller.multi_act(
                parsed_actions, browser_env.browser_context
            )

            # Update state with results
            state["environment_output"] = {
                "success": all(not r.error for r in results),
                "result": {"action_results": [r.model_dump() for r in results]},
                "error": next((r.error for r in results if r.error), None),
            }

            # Check if task is complete
            task_complete = self._evaluate_task_completion(state, results)
            if task_complete:
                state["done"] = True
                return Command(goto="end")

            # Continue agent loop
            return Command(goto="chain_of_thought")

        except Exception as e:
            state["error"] = str(e)
            return Command(goto="coordinator")

    def _prepare_messages(self, state: AgentState, browser_state: Dict) -> List[Dict]:
        """Prepare messages for LLM including browser state"""
        return [
            SystemMessage(content="You are a browser automation expert."),
            HumanMessage(content=state["task"]),
            SystemMessage(
                content=f"Current browser state:\nURL: {browser_state.get('url')}\nTitle: {browser_state.get('title')}"
            ),
        ]

    def _parse_llm_response(self, ai_message) -> List[ActionModel]:
        """Parse LLM response into ActionModel instances"""
        if not ai_message.additional_kwargs.get("function_call"):
            return []

        try:
            tool_calls = json.loads(
                ai_message.additional_kwargs["function_call"]["arguments"]
            )
            return [ActionModel(**action) for action in tool_calls.get("actions", [])]
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return []

    def _evaluate_task_completion(
        self, state: AgentState, results: List[ActionResult]
    ) -> bool:
        """Evaluate if task is complete based on results"""
        if not results:
            return False
        # Add your task completion logic here
        return False


# NOTE: Terminal and Code environment nodes are temporarily commented out
# Will be re-enabled once browser environment flow is stable and working
# See todo.md for implementation timeline

# class TerminalEnvNode:
#     """Handles terminal environment execution with own planning"""

#     def __init__(self):
#         self.name = "terminal_env"

#     async def __call__(self, state: AgentState, config: Dict):
#         """Make node callable for LangGraph and ensure async execution"""
#         return await self.ainvoke(state, config)

#     def invoke(self, state: AgentState, config: Dict):
#         """Prevent sync execution"""
#         raise NotImplementedError("Terminal environment requires async execution")

#     async def ainvoke(self, state: AgentState, config: Dict) -> Dict:
#         """Plan and execute terminal actions"""
#         llm = config.get("configurable", {}).get("llm")
#         env_registry = config.get("configurable", {}).get("env_registry", {})

#         # Get tools
#         terminal_env = env_registry.get(EnvironmentType.TERMINAL)
#         if not terminal_env:
#             return {"error": "Terminal environment not available"}

#         # Plan next action using available tools
#         tools = terminal_env.tool_registry.get_openai_functions()

#         messages = [
#             SystemMessage(content="You are a terminal automation expert"),
#             HumanMessage(
#                 content=f"Task: {state['task']}\nWhat terminal action should we take next?"
#             ),
#         ]

#         function_call = await llm.ainvoke(messages, functions=tools)

#         # Execute planned action
#         if function_call.additional_kwargs.get("function_call"):
#             tool_name = function_call.additional_kwargs["function_call"]["name"]
#             tool_args = json.loads(
#                 function_call.additional_kwargs["function_call"]["arguments"]
#             )

#             action = {"type": tool_name, "params": tool_args}
#             result = await terminal_env.execute(action)

#             state["environment_output"] = result.model_dump()
#             if result.error:
#                 state["error"] = result.error

#         return state


# class CodeEnvNode:
#     """Handles code environment execution with own planning"""

#     def __init__(self):
#         self.name = "code_env"

#     async def __call__(self, state: AgentState, config: Dict):
#         """Make node callable for LangGraph and ensure async execution"""
#         return await self.ainvoke(state, config)

#     def invoke(self, state: AgentState, config: Dict):
#         """Prevent sync execution"""
#         raise NotImplementedError("Code environment requires async execution")

#     async def ainvoke(self, state: AgentState, config: Dict) -> Dict:
#         """Plan and execute code actions"""
#         llm = config.get("configurable", {}).get("llm")
#         env_registry = config.get("configurable", {}).get("env_registry", {})

#         # Get tools
#         code_env = env_registry.get(EnvironmentType.CODE)
#         if not code_env:
#             return {"error": "Code environment not available"}

#         # Plan next action using available tools
#         tools = code_env.tool_registry.get_openai_functions()

#         messages = [
#             SystemMessage(content="You are a code automation expert"),
#             HumanMessage(
#                 content=f"Task: {state['task']}\nWhat code action should we take next?"
#             ),
#         ]

#         function_call = await llm.ainvoke(messages, functions=tools)

#         # Execute planned action
#         if function_call.additional_kwargs.get("function_call"):
#             tool_name = function_call.additional_kwargs["function_call"]["name"]
#             tool_args = json.loads(
#                 function_call.additional_kwargs["function_call"]["arguments"]
#             )

#             action = {"type": tool_name, "params": tool_args}
#             result = await code_env.execute(action)

#             state["environment_output"] = result.model_dump()
#             if result.error:
#                 state["error"] = result.error

#         return state


def chain_of_thought_sync(state: AgentState) -> AgentState:
    """Synchronous wrapper for chain of thought processing"""
    # Initialize brain state if needed
    if not state.get("brain"):
        state["brain"] = BrainState().model_dump()
    return state


async def chain_of_thought(
    state: AgentState, llm=None, env_registry: Optional[Dict[str, Any]] = None
) -> AgentState:
    """Enhanced chain of thought with structured output"""
    state = chain_of_thought_sync(state)

    # Get available tools for current environment
    current_env = state.get("current_env", "browser_env").replace("_env", "")
    env = env_registry.get(current_env) if env_registry else None

    if env and hasattr(env, "tool_registry"):
        tools = env.tool_registry.get_openai_functions()
        messages = [
            HumanMessage(content=state["task"]),
            SystemMessage(content="Use the available tools to accomplish the task."),
        ]

        function_call = llm.invoke(messages, functions=tools)

        # Handle tool calls
        if function_call.additional_kwargs.get("function_call"):
            tool_name = function_call.additional_kwargs["function_call"]["name"]
            tool_args = json.loads(
                function_call.additional_kwargs["function_call"]["arguments"]
            )
            state["tools_used"] = state.get("tools_used", []) + [{tool_name: tool_args}]

    # Update brain state
    if state.get("environment_output"):
        output = state["environment_output"]
        brain = BrainState(
            prev_action_evaluation=f"{'Success' if output.get('success') else 'Failed'} - {output.get('result', {}).get('action_result', '')}",
            important_contents=output.get("result", {}).get("extracted_content", ""),
            task_progress=output.get("result", {}).get("task_progress", ""),
            future_plans="",  # No longer using subtask-based plans
            thought=output.get("result", {}).get("thought", ""),
            summary=_generate_summary(state),
        )
        state["brain"] = brain.model_dump()

    return state


def _generate_summary(state: AgentState) -> str:
    """Generate action summary"""
    current_env = state.get("current_env", "")
    return f"Using {current_env} to complete task: {state.get('task', '')}"


async def coordinate_environments(state: AgentState) -> Dict:
    """Coordinates transitions between environments"""
    output = state.get("environment_output", {})

    if output.get("error"):
        state["error"] = output["error"]
        state["next_node"] = "router"
    elif output.get("next_env"):
        state["current_env"] = output["next_env"]
        state["next_node"] = "router"
    elif output.get("success"):
        state["next_node"] = "end"
        state["done"] = True
    else:
        state["next_node"] = "router"

    return state


def create_agent_graph() -> Graph:
    """Creates the main agent workflow graph with agent loop behavior"""
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("chain_of_thought", ChainOfThoughtNode())
    workflow.add_node("router", RouterNode())
    workflow.add_node("browser_env", BrowserEnvNode())
    workflow.add_node("coordinator", coordinate_environments)

    # Add end node that marks task as complete
    async def end_node(state: AgentState) -> AgentState:
        state["done"] = True
        return state

    workflow.add_node("end", end_node)

    # Set up agent loop with conditional edges
    workflow.add_edge(START, "chain_of_thought")
    workflow.add_edge("chain_of_thought", "router")
    workflow.add_edge("router", "browser_env")

    # Browser environment can loop back through chain of thought
    workflow.add_edge("browser_env", "coordinator")
    workflow.add_edge("coordinator", "chain_of_thought")

    # Add end conditions
    workflow.add_conditional_edges(
        "coordinator",
        lambda state: (
            "end" if state.get("done") or state.get("error") else "chain_of_thought"
        ),
    )

    # Connect end node to graph END marker
    workflow.add_edge("end", END)

    return workflow.compile()
