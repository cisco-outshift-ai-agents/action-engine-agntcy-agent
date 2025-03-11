from typing import Dict


# TODO: Tighter coupling between this and the browser_use controller


def get_action_schemas() -> Dict[str, Dict]:
    """Get formatted documentation of all action schemas"""
    return {
        "done": {
            "example": {"done": {"text": "Task completed"}},
            "description": "Mark task as complete",
            "required": ["text"],
            "properties": {"text": {"type": "string"}},
        },
        "search_google": {
            "example": {"search_google": {"query": "python programming"}},
            "description": "Search Google in the current tab",
            "required": ["query"],
            "properties": {"query": {"type": "string"}},
        },
        "go_to_url": {
            "example": {"go_to_url": {"url": "https://example.com"}},
            "description": "Navigate to URL in the current tab",
            "required": ["url"],
            "properties": {"url": {"type": "string"}},
        },
        "go_back": {
            "example": {"go_back": {}},
            "description": "Go back to previous page",
            "required": [],
            "properties": {},
        },
        "click_element": {
            "example": {"click_element": {"index": 1, "xpath": None}},
            "description": "Click an element by index or xpath",
            "required": ["index"],
            "properties": {
                "index": {"type": "integer"},
                "xpath": {"type": ["string", "null"], "default": None},
            },
        },
        "input_text": {
            "example": {
                "input_text": {"index": 1, "text": "search query", "xpath": None}
            },
            "description": "Input text into an interactive element",
            "required": ["index", "text"],
            "properties": {
                "index": {"type": "integer"},
                "text": {"type": "string"},
                "xpath": {"type": ["string", "null"], "default": None},
            },
        },
        "switch_tab": {
            "example": {"switch_tab": {"page_id": 1}},
            "description": "Switch to a different browser tab",
            "required": ["page_id"],
            "properties": {"page_id": {"type": "integer"}},
        },
        "open_tab": {
            "example": {"open_tab": {"url": "https://example.com"}},
            "description": "Open URL in new tab",
            "required": ["url"],
            "properties": {"url": {"type": "string"}},
        },
        "extract_content": {
            "example": {"extract_content": {"include_links": True}},
            "description": "Extract page content as text or markdown with links",
            "required": ["include_links"],
            "properties": {"include_links": {"type": "boolean"}},
        },
        "scroll_down": {
            "example": {"scroll_down": {"amount": None}},
            "description": "Scroll down the page by pixel amount",
            "required": [],
            "properties": {"amount": {"type": ["integer", "null"], "default": None}},
        },
        "scroll_up": {
            "example": {"scroll_up": {"amount": None}},
            "description": "Scroll up the page by pixel amount",
            "required": [],
            "properties": {"amount": {"type": ["integer", "null"], "default": None}},
        },
        "send_keys": {
            "example": {"send_keys": {"keys": "Control+A"}},
            "description": "Send special keys or keyboard shortcuts",
            "required": ["keys"],
            "properties": {"keys": {"type": "string"}},
        },
        "scroll_to_text": {
            "example": {"scroll_to_text": {"text": "Submit"}},
            "description": "Scroll to specific text on the page",
            "required": ["text"],
            "properties": {"text": {"type": "string"}},
        },
        "get_dropdown_options": {
            "example": {"get_dropdown_options": {"index": 1}},
            "description": "Get all options from a dropdown element",
            "required": ["index"],
            "properties": {"index": {"type": "integer"}},
        },
        "select_dropdown_option": {
            "example": {"select_dropdown_option": {"index": 1, "text": "Option 1"}},
            "description": "Select option from dropdown by text",
            "required": ["index", "text"],
            "properties": {
                "index": {"type": "integer"},
                "text": {"type": "string"},
            },
        },
        "copy_to_clipboard": {
            "example": {"copy_to_clipboard": {"text": "Copy this text"}},
            "description": "Copy text to clipboard",
            "required": ["text"],
            "properties": {"text": {"type": "string"}},
        },
        "paste_from_clipboard": {
            "example": {"paste_from_clipboard": {}},
            "description": "Paste text from clipboard",
            "required": [],
            "properties": {},
        },
    }
