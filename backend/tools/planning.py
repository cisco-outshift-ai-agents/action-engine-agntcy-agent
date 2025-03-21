import logging
import traceback
from enum import Enum
from typing import Dict, List, Optional, Union

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from graph.environments.planning import Plan, PlanningEnvironment

from .base import ToolResult

logger = logging.getLogger(__name__)


class PlanCommand(str, Enum):
    """Available planning commands"""

    CREATE = "create"
    UPDATE_PLAN = "update_plan"
    MARK_STEPS = "mark_steps"


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
    step_updates: Optional[List[Dict[str, Union[int, str]]]] = None,  # For bulk updates
    config: RunnableConfig = None,
) -> ToolResult:
    """
    A simplified planning API for creating and updating plans.

    Commands:
    - CREATE: Create a new plan. Requires 'task' (used as title if no title provided) and 'steps' array.
      Example: {
          "command": "create",
          "task": "Build a website",
          "steps": ["Design layout", "Code HTML", "Add CSS"]
      }

    - UPDATE_PLAN: Replace all steps in a plan. Requires 'plan_id' and new 'steps' array. Optional 'title' update.
      Note: This resets all step statuses to "not_started".
      Example: {
          "command": "update_plan",
          "plan_id": "plan_0",
          "steps": ["New step 1", "New step 2"]
      }

    - MARK_STEPS: Update multiple steps' statuses at once. Requires 'plan_id' and 'step_updates' array.
      Example: {
          "command": "mark_steps",
          "plan_id": "plan_0",
          "step_updates": [
              { "index": 0, "status": "completed" },
              { "index": 1, "status": "completed" },
              { "index": 2, "status": "in_progress" }
          ]
      }

    Args:
        command: The planning command to execute (create, update_plan, or mark_steps)
        plan_id: Plan identifier (required for update_plan and mark_steps)
        title: Plan title (optional for create and update_plan)
        task: Task description (required for create)
        steps: List of plan steps (required for create and update_plan)
        step_updates: List of step updates, each with index and status (required for mark_steps)
    """
    logger.info(f"Planning tool invoked with command: {command}")

    if not config or "configurable" not in config:
        logger.error("[PlanningTool] No configurable in config")
        return ToolResult(error="Config missing 'configurable' key")

    planning_env = config["configurable"].get("planning_environment")
    if not isinstance(planning_env, PlanningEnvironment):
        logger.error("No planning_environment in configurable")
        return ToolResult(error="Planning environment not initialized")

    try:
        if command == PlanCommand.CREATE:
            if not task:
                return ToolResult(error="'task' is required for create command")
            if not steps:
                return ToolResult(error="'steps' array is required for create command")

            plan_id = f"plan_{len(planning_env._plans)}"
            plan = Plan(
                plan_id=plan_id,
                title=title or task,
                steps=steps,
                step_statuses=["not_started"] * len(steps),
                step_notes=[""] * len(steps),
            )
            planning_env.create_plan(plan)

        elif command == PlanCommand.UPDATE_PLAN:
            if not plan_id:
                return ToolResult(error="'plan_id' is required for update_plan command")
            if not steps:
                return ToolResult(
                    error="'steps' array is required for update_plan command"
                )

            updates = {
                "steps": steps,
                "step_statuses": ["not_started"] * len(steps),
                "step_notes": [""] * len(steps),
            }
            if title:
                updates["title"] = title

            planning_env.update_plan(plan_id, updates)

        elif command == PlanCommand.MARK_STEPS:
            if not plan_id:
                return ToolResult(error="'plan_id' is required for mark_steps command")
            if not step_updates:
                return ToolResult(
                    error="'step_updates' array is required for mark_steps command"
                )

            plan = planning_env.get_plan(plan_id)
            if not plan:
                return ToolResult(error=f"No plan found with ID: {plan_id}")

            updates = {"step_statuses": list(plan.step_statuses)}

            for update in step_updates:
                if not isinstance(update, dict):
                    return ToolResult(error="Each step update must be a dictionary")

                index = update.get("index")
                status = update.get("status")

                if index is None:
                    return ToolResult(error="Each step update requires an 'index'")
                if not isinstance(index, int):
                    return ToolResult(error="Step index must be an integer")
                if not 0 <= index < len(plan.steps):
                    return ToolResult(
                        error=f"Invalid step index: {index}. Must be between 0 and {len(plan.steps)-1}"
                    )

                if not status:
                    return ToolResult(error="Each step update requires a 'status'")
                if status not in [s.value for s in StepStatus]:
                    return ToolResult(error=f"Invalid status: {status}")

                updates["step_statuses"][index] = status

            planning_env.update_plan(plan_id, updates)

        plan = planning_env.get_plan(plan_id)
        return ToolResult(
            output=planning_env.format_plan(plan) if plan else "No plan found"
        )

    except Exception as e:
        traceback.print_exc()
        return ToolResult(error=str(e))
