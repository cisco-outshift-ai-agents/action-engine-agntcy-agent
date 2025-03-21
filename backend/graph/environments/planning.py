from typing import Dict, List, Literal, Optional, Union
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel, Field


class Step(BaseModel):
    """Step model for representing a single step with optional substeps"""

    content: str
    status: Literal["not_started", "in_progress", "completed", "blocked"] = (
        "not_started"
    )
    notes: str = ""
    substeps: List["Step"] = Field(default_factory=list)


Step.model_rebuild()  # Required for recursive Pydantic models


class Plan(BaseModel):
    """Plan model for tracking hierarchical steps and progress"""

    plan_id: str
    title: str
    steps: List[Step]


class PlanningEnvironment:
    """Manages global planning state as a singleton"""

    _instance = None
    _plans: Dict[str, Plan]
    _current_plan_id: Optional[str]

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PlanningEnvironment, cls).__new__(cls)
            cls._instance._plans = {}
            cls._instance._current_plan_id = None
        return cls._instance

    def get_plan(self, plan_id: Optional[str] = None) -> Optional[Plan]:
        """Get plan by ID or current active plan"""
        if not plan_id:
            plan_id = self._current_plan_id
        return self._plans.get(plan_id)

    def set_active_plan(self, plan_id: str) -> None:
        """Set active plan"""
        if plan_id not in self._plans:
            raise ValueError(f"No plan found with ID: {plan_id}")
        self._current_plan_id = plan_id

    def create_plan(self, plan: Plan) -> None:
        """Create new plan"""
        self._plans[plan.plan_id] = plan
        self._current_plan_id = plan.plan_id

    def update_plan(self, plan_id: str, updates: Dict) -> None:
        """Update existing plan"""
        if plan_id not in self._plans:
            raise ValueError(f"No plan found with ID: {plan_id}")
        plan = self._plans[plan_id]

        # Handle nested step updates
        if "step_index" in updates and "step_status" in updates:
            index_path = updates.pop("step_index")
            new_status = updates.pop("step_status")

            # Handle both single index and nested index paths
            indices = index_path if isinstance(index_path, list) else [index_path]

            current_step = None
            current_steps = plan.steps

            # Navigate to the correct step
            for idx in indices[:-1]:
                if 0 <= idx < len(current_steps):
                    current_step = current_steps[idx]
                    current_steps = current_step.substeps
                else:
                    raise ValueError(f"Invalid step index: {idx}")

            # Update the final step's status
            final_idx = indices[-1]
            if 0 <= final_idx < len(current_steps):
                current_steps[final_idx].status = new_status
            else:
                raise ValueError(f"Invalid step index: {final_idx}")

        # Apply any other updates to the plan
        for key, value in updates.items():
            setattr(plan, key, value)

    def delete_plan(self, plan_id: str) -> None:
        """Delete a plan"""
        if plan_id not in self._plans:
            raise ValueError(f"No plan found with ID: {plan_id}")
        del self._plans[plan_id]
        if self._current_plan_id == plan_id:
            self._current_plan_id = None

    def list_plans(self) -> Dict[str, Plan]:
        """List all plans"""
        return self._plans

    def _calculate_step_stats(self, steps: List[Step]) -> Dict[str, int]:
        """Calculate statistics for steps recursively"""
        stats = {
            "total": 0,
            "completed": 0,
            "in_progress": 0,
            "blocked": 0,
            "not_started": 0,
        }

        for step in steps:
            stats["total"] += 1
            stats[step.status] += 1

            # Recursively process substeps
            if step.substeps:
                substep_stats = self._calculate_step_stats(step.substeps)
                for key in stats:
                    if key != "total":  # Don't double count total
                        stats[key] += substep_stats[key]
                stats["total"] += substep_stats["total"]

        return stats

    def _format_steps(self, steps: List[Step], level: int = 0) -> str:
        """Format steps recursively with proper indentation"""
        output = ""
        indent = "    " * level

        for i, step in enumerate(steps):
            status_symbol = {
                "not_started": "[ ]",
                "in_progress": "[→]",
                "completed": "[✓]",
                "blocked": "[!]",
            }.get(step.status, "[ ]")

            output += f"{indent}{i}. {status_symbol} {step.content}\n"
            if step.notes:
                output += f"{indent}   Notes: {step.notes}\n"

            if step.substeps:
                output += self._format_steps(step.substeps, level + 1)

        return output

    def format_plan(self, plan: Plan) -> str:
        """Format plan for display with nested steps"""
        output = f"The current plan: {plan.title} (ID: {plan.plan_id})\n"
        output += "=" * len(output) + "\n\n"

        # Calculate progress statistics recursively
        stats = self._calculate_step_stats(plan.steps)
        total = stats["total"]
        completed = stats["completed"]

        output += f"Progress: {completed}/{total} steps completed "
        if total > 0:
            percentage = (completed / total) * 100
            output += f"({percentage:.1f}%)\n"
        else:
            output += "(0%)\n"

        output += (
            f"Status: {completed} completed, {stats['in_progress']} in progress, "
            f"{stats['blocked']} blocked, {stats['not_started']} not started\n\n"
        )
        output += "Steps:\n"
        output += self._format_steps(plan.steps)

        return output

    def get_message_for_current_plan(self) -> HumanMessage:
        plan = self.get_plan()
        if not plan:
            return HumanMessage(content="No plan available")

        formatted_plan = self.format_plan(plan)
        return HumanMessage(content=formatted_plan)
