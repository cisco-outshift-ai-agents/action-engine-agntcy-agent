from typing import List

from pydantic import BaseModel, Field


class TaskAnalysis(BaseModel):
    """Simple environment selection model"""

    primary_environment: str = Field(
        description="The main environment to use (browser/terminal/code)",
        pattern="^(browser|terminal|code)$",
    )
    reasoning: str = Field(description="Why this environment was chosen")
    required_tools: List[str] = Field(default_factory=list)
