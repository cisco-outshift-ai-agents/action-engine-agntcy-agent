import logging
from typing import Dict, List
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langgraph.types import Command

from core.types import AgentState

logger = logging.getLogger(__name__)


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
