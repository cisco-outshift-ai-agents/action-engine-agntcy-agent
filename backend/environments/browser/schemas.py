from typing import Any, Dict, List
from pydantic import BaseModel, Field
from core.types import BrainState


class BrowserResponse(BaseModel):
    """Complete browser action response"""

    current_state: BrainState
    action: List[Dict[str, Dict[str, Any]]] = Field(
        description="List of actions to execute. Each action should be in format: "
        "{action_name: {param1: value1, param2: value2}}",
        examples=[
            [
                {"go_to_url": {"url": "https://example.com"}},
                {"click_element": {"index": 1}},
                {"done": {"text": "Task completed"}},
            ]
        ],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "current_state": {
                        "prev_action_evaluation": "Unknown",
                        "important_contents": "",
                        "task_progress": "",
                        "future_plans": "",
                        "thought": "Need to navigate to website",
                        "summary": "Opening webpage",
                    },
                    "action": [{"go_to_url": {"url": "https://www.wikipedia.org"}}],
                }
            ]
        }
    }
