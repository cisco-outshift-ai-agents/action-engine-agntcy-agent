from dataclasses import dataclass
from typing import Type
from browser_use.agent.views import AgentOutput
from browser_use.controller.registry.views import ActionModel
from pydantic import BaseModel, ConfigDict, Field, create_model


@dataclass
class CustomAgentStepInfo:
    step_number: int
    max_steps: int
    task: str
    add_infos: str = ""
    memory: str = ""
    task_progress: str = ""
    future_plans: str = ""


class CustomAgentBrain(BaseModel):
    """Current state of the agent"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    prev_action_evaluation: str = ""
    important_contents: str = ""
    task_progress: str = ""
    future_plans: str = ""
    thought: str = ""
    summary: str = ""


class DoneTextFormat(BaseModel):
    """Format for the text field in done actions"""

    type: str


class DoneAction(BaseModel):
    """Format for done actions"""

    text: DoneTextFormat


class CustomAgentOutput(AgentOutput):
    """Output model for agent with support for the done action format

    @dev note: this model is extended with custom actions in AgentService. You can also use some fields that are not in this model as provided by the linter, as long as they are registered in the DynamicActions model.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    current_state: CustomAgentBrain = Field(default_factory=CustomAgentBrain)
    action: list[ActionModel] = Field(default_factory=list)

    @staticmethod
    def type_with_custom_actions(
        custom_actions: Type[ActionModel],
    ) -> Type["CustomAgentOutput"]:
        """Extend actions with custom actions"""
        return create_model(
            "CustomAgentOutput",
            __base__=CustomAgentOutput,
            action=(
                list[custom_actions],
                Field(...),
            ),  # Properly annotated field with no default
            __module__=CustomAgentOutput.__module__,
        )
