from typing import Dict, List, Literal, Optional, Union, Any
from enum import Enum
from pydantic import BaseModel, Field

from .base import ToolResult
from langchain_core.tools import tool


class Plan(BaseModel):
    """Plan model for tracking steps and progress"""

    plan_id: str
    title: str
    steps: List[str]
    step_statuses: List[Literal["not_started", "in_progress", "completed", "blocked"]]
    step_notes: List[str]


class PlanManager:
    """Manages plan state"""

    _plans: Dict[str, Plan] = {}
    _current_plan_id: Optional[str] = None

    @classmethod
    def get_plan(cls, plan_id: Optional[str] = None) -> Optional[Plan]:
        """Get plan by ID or current active plan"""
        if not plan_id:
            plan_id = cls._current_plan_id
        return cls._plans.get(plan_id)

    @classmethod
    def set_active_plan(cls, plan_id: str) -> None:
        """Set active plan"""
        if plan_id not in cls._plans:
            raise ValueError(f"No plan found with ID: {plan_id}")
        cls._current_plan_id = plan_id

    @classmethod
    def format_plan(cls, plan: Plan) -> str:
        """Format plan for display"""
        output = f"Plan: {plan.title} (ID: {plan.plan_id})\n"
        output += "=" * len(output) + "\n\n"

        # Calculate progress statistics
        total_steps = len(plan.steps)
        completed = sum(1 for status in plan.step_statuses if status == "completed")
        in_progress = sum(1 for status in plan.step_statuses if status == "in_progress")
        blocked = sum(1 for status in plan.step_statuses if status == "blocked")
        not_started = sum(1 for status in plan.step_statuses if status == "not_started")

        output += f"Progress: {completed}/{total_steps} steps completed "
        if total_steps > 0:
            percentage = (completed / total_steps) * 100
            output += f"({percentage:.1f}%)\n"
        else:
            output += "(0%)\n"

        output += f"Status: {completed} completed, {in_progress} in progress, {blocked} blocked, {not_started} not started\n\n"
        output += "Steps:\n"

        # Add each step with its status and notes
        for i, (step, status, notes) in enumerate(
            zip(plan.steps, plan.step_statuses, plan.step_notes)
        ):
            status_symbol = {
                "not_started": "[ ]",
                "in_progress": "[→]",
                "completed": "[✓]",
                "blocked": "[!]",
            }.get(status, "[ ]")

            output += f"{i}. {status_symbol} {step}\n"
            if notes:
                output += f"   Notes: {notes}\n"

        return output


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


@tool
async def planning_tool(
    command: PlanCommand,
    plan_id: Optional[str] = None,
    title: Optional[str] = None,
    task: Optional[str] = None,
    steps: Optional[List[str]] = None,
    step_index: Optional[int] = None,
    step_status: Optional[StepStatus] = None,
    step_notes: Optional[str] = None,
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
    try:
        if command == PlanCommand.CREATE:
            if not plan_id:
                return ToolResult(error="plan_id is required for create command")

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
            PlanManager._plans[plan.plan_id] = plan
            PlanManager._current_plan_id = plan.plan_id

        elif command == PlanCommand.UPDATE:
            plan_id = plan_id
            if not plan_id:
                return ToolResult(error="plan_id is required for update command")

            if plan_id not in PlanManager._plans:
                return ToolResult(error=f"No plan found with ID: {plan_id}")

            plan = PlanManager._plans[plan_id]

            if title:
                plan.title = title

            if steps:
                if not isinstance(steps, list):
                    return ToolResult(error="Steps must be a list")

                new_steps = steps
                old_steps = plan.steps
                old_statuses = plan.step_statuses
                old_notes = plan.step_notes

                new_statuses = []
                new_notes = []

                for i, step in enumerate(new_steps):
                    if i < len(old_steps) and step == old_steps[i]:
                        new_statuses.append(old_statuses[i])
                        new_notes.append(old_notes[i])
                    else:
                        new_statuses.append("not_started")
                        new_notes.append("")

                plan.steps = new_steps
                plan.step_statuses = new_statuses
                plan.step_notes = new_notes

        elif command == PlanCommand.LIST:
            if not PlanManager._plans:
                return ToolResult(output="No plans available")

            output = ["Available plans:"]
            for plan_id, plan in PlanManager._plans.items():
                completed = sum(1 for s in plan.step_statuses if s == "completed")
                total = len(plan.steps)
                percentage = (completed / total * 100) if total > 0 else 0
                active = " (active)" if plan_id == PlanManager._current_plan_id else ""

                output.append(
                    f"• {plan_id}{active}: {plan.title} - "
                    f"{completed}/{total} steps ({percentage:.1f}%)"
                )

            return ToolResult(output="\n".join(output))

        elif command == PlanCommand.GET:
            plan_id = plan_id or PlanManager._current_plan_id
            if not plan_id:
                return ToolResult(error="No plan ID provided and no active plan set")

            plan = PlanManager.get_plan(plan_id)
            if not plan:
                return ToolResult(error=f"No plan found with ID: {plan_id}")

        elif command == PlanCommand.SET_ACTIVE:
            plan_id = plan_id
            if not plan_id:
                return ToolResult(error="plan_id is required for set_active command")

            if plan_id not in PlanManager._plans:
                return ToolResult(error=f"No plan found with ID: {plan_id}")

            PlanManager._current_plan_id = plan_id

        elif command == PlanCommand.MARK_STEP:
            plan_id = plan_id or PlanManager._current_plan_id
            if not plan_id:
                return ToolResult(error="No plan ID provided and no active plan set")

            plan = PlanManager.get_plan(plan_id)
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

            if plan_id not in PlanManager._plans:
                return ToolResult(error=f"No plan found with ID: {plan_id}")

            del PlanManager._plans[plan_id]
            if PlanManager._current_plan_id == plan_id:
                PlanManager._current_plan_id = None

            return ToolResult(output=f"Plan {plan_id} deleted successfully")

        if command != PlanCommand.LIST and command != PlanCommand.DELETE:
            plan = PlanManager.get_plan(plan_id)
            return ToolResult(
                output=PlanManager.format_plan(plan) if plan else "No plan found"
            )

    except Exception as e:
        return ToolResult(error=str(e))
