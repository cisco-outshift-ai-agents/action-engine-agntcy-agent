from typing import Dict


def get_action_schemas() -> Dict[str, str]:
    """Get formatted documentation of all action schemas"""
    return {
        "go_to_url": {
            "example": {"go_to_url": {"url": "https://example.com"}},
            "description": "Navigate to a URL",
            "required": ["url"],
        },
        "click_element": {
            "example": {"click_element": {"index": 1}},
            "description": "Click an element by index",
            "required": ["index"],
        },
        "input_text": {
            "example": {"input_text": {"index": 1, "text": "search query"}},
            "description": "Input text into an element",
            "required": ["index", "text"],
        },
        "done": {
            "example": {"done": {"text": "Task completed"}},
            "description": "Mark task as complete",
            "required": ["text"],
        },
    }
