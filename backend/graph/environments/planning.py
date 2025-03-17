from typing import Dict, List, Literal, Optional
from pydantic import BaseModel
from langchain_core.messages import AIMessage


class Plan(BaseModel):
    """Plan model for tracking steps and progress"""

    plan_id: str
    title: str
    steps: List[str]
    step_statuses: List[Literal["not_started", "in_progress", "completed", "blocked"]]
    step_notes: List[str]


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

    def format_plan(cls, plan: Plan) -> str:
        """Format plan for display"""
        output = f"The current plan: {plan.title} (ID: {plan.plan_id})\n"
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

    def get_ai_message_for_current_plan(self) -> AIMessage:
        plan = self.get_plan()
        if not plan:
            return AIMessage(content="No plan available")

        formatted_plan = self.format_plan(plan)

        return AIMessage(content=formatted_plan)
