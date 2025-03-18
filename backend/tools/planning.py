import logging
from typing import List, Optional
from enum import Enum
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig

from .base import ToolResult
from graph.environments.planning import Plan, PlanningEnvironment
import traceback

logger = logging.getLogger(__name__)


class PlanCommand(str, Enum):
    """Available planning commands"""

    CREATE = "create"
    UPDATE = "update"
    LIST = "list"
    GET = "get"
    SET_ACTIVE = "set_active"
    MARK_STEP = "mark_step"
    DELETE = "delete"


class StepStatus(str, Enum):
    """Step completion status"""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"


@tool("planning")
async def planning_tool(
    command: PlanCommand,
    plan_id: Optional[str] = None,
    title: Optional[str] = None,
    task: Optional[str] = None,
    steps: Optional[List[str]] = None,
    step_index: Optional[int] = None,
    step_status: Optional[StepStatus] = None,
    step_notes: Optional[str] = None,
    config: RunnableConfig = None,  # Changed to explicitly use RunnableConfig
) -> ToolResult:
    """
    A planning tool that allows the agent to create and manage plans for solving complex tasks.
    Supports creating plans, updating steps, tracking progress, and managing multiple plans.

    Args:
        command: The planning command to execute
        plan_id: Identifier for the plan
        title: Title for the plan
        task: Task description for plan creation
        steps: List of steps for the plan
        step_index: Index of step to modify
        step_status: Status to set for a step
        step_notes: Notes to add to a step
    """
    logger.info(f"Planning tool invoked with command: {command}")

    if not config or "configurable" not in config:
        logger.error("[PlanningTool] No configurable in config")
        return ToolResult(error="Config missing 'configurable' key")

    planning_env = config["configurable"].get("planning_environment")
    if not isinstance(planning_env, PlanningEnvironment):
        logger.error("No planning_environment in configurable")
        return ValueError("Planning environment not initialized")

    try:
        if command == PlanCommand.CREATE:
            plan_id = plan_id or f"plan_{len(planning_env._plans)}"

            title = title or task or "Untitled Plan"
            if not task:
                return ToolResult(error="task is required for create command")

            steps = steps or [task]

            plan = Plan(
                plan_id=plan_id,
                title=title,
                steps=steps,
                step_statuses=["not_started"] * len(steps),
                step_notes=[""] * len(steps),
            )
            planning_env.create_plan(plan)

        elif command == PlanCommand.UPDATE:
            if not plan_id:
                return ToolResult(error="plan_id is required for update command")

            updates = {}
            if title:
                updates["title"] = title
            if steps:
                updates["steps"] = steps
                updates["step_statuses"] = ["not_started"] * len(steps)
                updates["step_notes"] = [""] * len(steps)

            planning_env.update_plan(plan_id, updates)

        elif command == PlanCommand.LIST:
            plans = planning_env.list_plans()
            if not plans:
                return ToolResult(output="No plans available")

            output = ["Available plans:"]
            for p_id, plan in plans.items():
                active = " (active)" if p_id == planning_env._current_plan_id else ""
                completed = sum(1 for s in plan.step_statuses if s == "completed")
                total = len(plan.steps)
                percentage = (completed / total * 100) if total > 0 else 0
                output.append(
                    f"• {p_id}{active}: {plan.title} - {completed}/{total} steps ({percentage:.1f}%)"
                )

            return ToolResult(output="\n".join(output))

        elif command == PlanCommand.GET:
            plan_id = plan_id or planning_env._current_plan_id
            if not plan_id:
                return ToolResult(error="No plan ID provided and no active plan set")

            plan = planning_env.get_plan(plan_id)
            if not plan:
                return ToolResult(error=f"No plan found with ID: {plan_id}")

        elif command == PlanCommand.SET_ACTIVE:
            plan_id = plan_id
            if not plan_id:
                return ToolResult(error="plan_id is required for set_active command")

            if plan_id not in planning_env._plans:
                return ToolResult(error=f"No plan found with ID: {plan_id}")

            planning_env._current_plan_id = plan_id

        elif command == PlanCommand.MARK_STEP:
            plan_id = plan_id or planning_env._current_plan_id
            if not plan_id:
                return ToolResult(error="No plan ID provided and no active plan set")

            plan = planning_env.get_plan(plan_id)
            if not plan:
                return ToolResult(error=f"No plan found with ID: {plan_id}")

            if step_index is None:
                return ToolResult(error="step_index is required for mark_step command")

            if not 0 <= step_index < len(plan.steps):
                return ToolResult(
                    error=f"Invalid step_index: {step_index}. Must be between 0 and {len(plan.steps)-1}"
                )

            if step_status:
                if step_status not in StepStatus:
                    return ToolResult(error=f"Invalid status: {step_status}")
                plan.step_statuses[step_index] = step_status

            if step_notes:
                plan.step_notes[step_index] = step_notes

        elif command == PlanCommand.DELETE:
            plan_id = plan_id
            if not plan_id:
                return ToolResult(error="plan_id is required for delete command")

            if plan_id not in planning_env._plans:
                return ToolResult(error=f"No plan found with ID: {plan_id}")

            del planning_env._plans[plan_id]
            if planning_env._current_plan_id == plan_id:
                planning_env._current_plan_id = None

            return ToolResult(output=f"Plan {plan_id} deleted successfully")

        if command != PlanCommand.LIST and command != PlanCommand.DELETE:
            plan = planning_env.get_plan(plan_id)
            return ToolResult(
                output=planning_env.format_plan(plan) if plan else "No plan found"
            )

    except Exception as e:
        traceback.print_exc()
        return ToolResult(error=str(e))
