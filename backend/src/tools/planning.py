import logging
import traceback
from enum import Enum
from typing import Dict, List, Optional, Union

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from src.graph.environments.planning import Plan, PlanningEnvironment, Step

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


def create_step_hierarchy(steps_data: List[Dict]) -> List[Step]:
    """Convert a list of step dictionaries into Step objects with proper nesting"""
    result = []
    for step_data in steps_data:
        step = Step(
            content=step_data["content"],
            status=step_data.get("status", "not_started"),
            notes=step_data.get("notes", ""),
        )
        if "substeps" in step_data:
            step.substeps = create_step_hierarchy(step_data["substeps"])
        result.append(step)
    return result


@tool("planning")
async def planning_tool(
    command: PlanCommand,
    plan_id: Optional[str] = None,
    title: Optional[str] = None,
    task: Optional[str] = None,
    steps: Optional[List[Dict]] = None,
    step_updates: Optional[List[Dict[str, Union[int, List[int], str]]]] = None,
    config: RunnableConfig = None,
) -> ToolResult:
    """
    A planning API for creating and updating hierarchical plans.

    Commands:
    - CREATE: Create a new plan with nested steps. Requires 'task' (used as title if no title provided) and 'steps' array.
      Note: This can be used either to create a new plan, or to refresh a plan if the user's task does not actively relate to the current plan.
      Example: {
          "command": "create",
          "task": "Build a website",
          "steps": [
              {
                  "content": "Setup project",
                  "substeps": [
                      { "content": "Create directory" },
                      { "content": "Initialize git" }
                  ]
              },
              {
                  "content": "Implement features",
                  "substeps": [
                      { "content": "Add homepage" },
                      { "content": "Add contact form" }
                  ]
              }
          ]
      }

    - UPDATE_PLAN: Replace all steps in a plan. Requires 'plan_id' and new 'steps' array. Optional 'title' update.
      Note: This resets all step statuses to "not_started".
      Example: {
          "command": "update_plan",
          "plan_id": "plan_0",
          "steps": [
              {
                  "content": "New main step",
                  "substeps": [
                      { "content": "New substep 1" },
                      { "content": "New substep 2" }
                  ]
              }
          ]
      }

    - MARK_STEPS: Update steps' statuses. Requires 'plan_id' and 'step_updates' array.
      For nested steps, use an array of indices to specify the path.
      Example: {
          "command": "mark_steps",
          "plan_id": "plan_0",
          "step_updates": [
              { "index": 0, "status": "completed" },              // Update main step
              { "index": [1, 0], "status": "in_progress" }       // Update first substep of second main step
          ]
      }

    Args:
        command: The planning command to execute
        plan_id: Plan identifier (required for update_plan and mark_steps)
        title: Plan title (optional for create and update_plan)
        task: Task description (required for create)
        steps: List of step dictionaries with optional nesting (required for create and update_plan)
        step_updates: List of step updates with indices and status (required for mark_steps)
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
            try:
                step_objects = create_step_hierarchy(steps)
            except Exception as e:
                return ToolResult(error=f"Invalid steps format: {str(e)}")

            plan = Plan(plan_id=plan_id, title=title or task, steps=step_objects)
            planning_env.create_plan(plan)

        elif command == PlanCommand.UPDATE_PLAN:
            if not plan_id:
                return ToolResult(error="'plan_id' is required for update_plan command")
            if not steps:
                return ToolResult(
                    error="'steps' array is required for update_plan command"
                )

            try:
                step_objects = create_step_hierarchy(steps)
            except Exception as e:
                return ToolResult(error=f"Invalid steps format: {str(e)}")

            updates = {"steps": step_objects}
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

            for update in step_updates:
                if not isinstance(update, dict):
                    return ToolResult(error="Each step update must be a dictionary")

                index = update.get("index")
                status = update.get("status")

                if index is None:
                    return ToolResult(error="Each step update requires an 'index'")
                if not status:
                    return ToolResult(error="Each step update requires a 'status'")
                if status not in [s.value for s in StepStatus]:
                    return ToolResult(error=f"Invalid status: {status}")

                # Convert single index to list format for consistency
                index_path = index if isinstance(index, list) else [index]

                try:
                    planning_env.update_plan(
                        plan_id, {"step_index": index_path, "step_status": status}
                    )
                except ValueError as e:
                    return ToolResult(error=str(e))

        plan = planning_env.get_plan(plan_id)
        return ToolResult(
            output=planning_env.format_plan(plan) if plan else "No plan found"
        )

    except Exception as e:
        traceback.print_exc()
        return ToolResult(error=str(e))
