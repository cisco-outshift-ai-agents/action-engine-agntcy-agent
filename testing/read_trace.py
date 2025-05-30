from dotenv import load_dotenv
from langsmith import Client
import argparse
import json
from datetime import datetime
import os
import re
from typing import Dict, List, Optional, Any, Union


def extract_element_type(element_desc: str) -> str:
    """
    Extract element type from HTML element description with semantic roles.
    Priority order:
    1. Role/type from aria attributes
    2. Input types
    3. Common semantic mappings
    4. Original tag if in common types
    5. Fallback to generic
    """
    if not element_desc or element_desc == "Description not found":
        return "browser"

    # Check for semantic roles first
    role_match = re.search(r'role="([^"]+)"', element_desc) or re.search(
        r'aria-role="([^"]+)"', element_desc
    )
    if role_match:
        role = role_match.group(1).lower()
        # High frequency roles from Mind2Web
        if role in {
            "button",
            "checkbox",
            "gridcell",
            "listbox",
            "menuitem",
            "option",
            "radio",
            "searchbox",
            "tab",
            "textbox",
            "combobox",
        }:
            return role

    # Check for input type
    type_match = re.search(r'type="([^"]+)"', element_desc)
    if type_match:
        input_type = type_match.group(1).lower()
        type_mapping = {
            "search": "searchbox",
            "text": "textbox",
            "checkbox": "checkbox",
            "radio": "radio",
        }
        return type_mapping.get(input_type, input_type)

    # Map HTML tags to most common Mind2Web types
    tag_match = re.match(r"<(\w+)", element_desc)
    if tag_match:
        tag = tag_match.group(1).lower()
        tag_mapping = {
            "a": "link",  # Very common (1569 occurrences)
            "button": "button",  # Most common (2017 occurrences)
            "input": "textbox",  # Common form element
            "select": "combobox",  # Common form element (369 occurrences)
            "img": "image",  # Common media type
            "textarea": "textbox",
        }
        if tag in tag_mapping:
            return tag_mapping[tag]

        # If tag is in common Mind2Web types, keep it
        if tag in {
            "button",
            "checkbox",
            "combobox",
            "div",
            "link",
            "listbox",
            "option",
            "radio",
            "searchbox",
            "textbox",
        }:
            return tag

    return "generic"  # Default fallback


def extract_element_description(element_desc: str) -> str:
    """
    Create a readable description from the element description.
    Prioritizes visible text content and semantic attributes.
    """
    if not element_desc or element_desc == "Description not found":
        return ""

    # Extract visible text content first - often most meaningful
    content_pattern = re.compile(r">\s*([^<>]+?)\s*<")
    content_matches = content_pattern.findall(element_desc)
    if content_matches:
        # Join multiple text segments, clean up whitespace
        text = " ".join(match.strip() for match in content_matches if match.strip())
        if text:
            return text

    # Extract aria label which often has meaningful descriptions
    aria_label = re.search(r'aria-label="([^"]+)"', element_desc)
    if aria_label:
        return aria_label.group(1)

    # Extract text attribute if present
    text_match = re.search(r'text="([^"]+)"', element_desc)
    if text_match:
        return text_match.group(1)

    # Extract placeholder which often contains helpful text
    placeholder = re.search(r'placeholder="([^"]+)"', element_desc)
    if placeholder:
        return placeholder.group(1)

    # Extract title attribute which may have descriptive text
    title = re.search(r'title="([^"]+)"', element_desc)
    if title:
        return title.group(1)

    # Extract name attribute if present
    name_match = re.search(r'name="([^"]+)"', element_desc)
    if name_match:
        return name_match.group(1)

    # Extract id attribute if present, clean up camelCase/snake_case
    id_match = re.search(r'id="([^"]+)"', element_desc)
    if id_match:
        id_text = id_match.group(1)
        # Split on camelCase and snake_case
        words = re.split("([A-Z][a-z]*)|_", id_text)
        # Clean and join words
        cleaned = " ".join(word for word in words if word)
        if cleaned:
            return cleaned.title()

    # Special cases
    if "searchInput" in element_desc:
        return "Search input"
    elif "search" in element_desc.lower():
        return "Search"

    # Extract any other text within quotation marks as a last resort
    quoted_text = re.search(r'"([^"]+)"', element_desc)
    if quoted_text:
        return quoted_text.group(1)

    return "element"


def format_action_repr(tool_call: Dict, element_desc: str) -> Optional[str]:
    """
    Format a tool call and element description into action_reprs format.
    """
    action = tool_call.get("args", {}).get("action", "")

    if action == "new_tab":
        url = tool_call.get("args", {}).get("url", "")
        domain = url.split("//")[-1].split("/")[0].replace("www.", "")
        return f"[browser] {domain.capitalize()} -> NAVIGATE: {url}"

    elif action == "click":
        element_type = extract_element_type(element_desc)
        description = extract_element_description(element_desc)
        return f"[{element_type}] {description} -> CLICK"

    elif action == "input_text":
        element_type = extract_element_type(element_desc)
        description = extract_element_description(element_desc)
        text = tool_call.get("args", {}).get("text", "")
        return f"[{element_type}] {description} -> TYPE: {text}"

    return None


def tool_calls_to_action_reprs(tool_calls_list, element_descriptions=None):
    """
    Convert directly provided tool calls and element descriptions to action_reprs format.

    Args:
        tool_calls_list: List of tool call dictionaries or a JSON string representation
        element_descriptions: Optional dict mapping indices to element descriptions or None

    Returns:
        List of action representations in the format used for LLM evaluation
    """
    action_reprs = []

    # If input is a string, parse it as JSON
    if isinstance(tool_calls_list, str):
        try:
            cleaned_json = tool_calls_list.replace("'", '"').replace('""', '"')
            tool_calls_list = json.loads(cleaned_json)
        except json.JSONDecodeError as e:
            print(f"Error parsing tool calls: {e}")
            return []

    # Process each tool call
    for tool_call in tool_calls_list:
        # Skip terminate actions
        if tool_call.get("name") == "terminate":
            continue

        action = tool_call.get("args", {}).get("action", "")

        # For new_tab actions, we don't need element description
        if action == "new_tab":
            action_repr = format_action_repr(tool_call, None)
            if action_repr:
                action_reprs.append(action_repr)
        # For other actions, we need the element description
        else:
            element_desc = None
            if element_descriptions:
                index = tool_call.get("args", {}).get("index")
                if index is not None:
                    # If element_descriptions is a dict mapping indices to descriptions
                    if isinstance(element_descriptions, dict):
                        element_desc = element_descriptions.get(index)
                    # If it's a single element description for the current tool call
                    elif isinstance(element_descriptions, str):
                        element_desc = element_descriptions

            action_repr = format_action_repr(tool_call, element_desc)
            if action_repr:
                action_reprs.append(action_repr)

    return action_reprs


def convert_direct_inputs_to_action_reprs(tool_call, element_desc=None):
    """
    Convert a single tool call string and element description to action_repr format.

    Args:
        tool_call_str: String representation of a tool call
        element_desc: Optional element description string

    Returns:
        An action representation string or None
    """
    # Parse tool call
    try:
        # Skip terminate actions
        if tool_call.get("name") == "terminate":
            return None

        return format_action_repr(tool_call, element_desc)
    except json.JSONDecodeError as e:
        print(f"Error parsing tool call: {e}")

    return None


def extract_run_info(run):
    """Extract relevant fields from a run object."""
    info = {
        "id": str(run.id) if hasattr(run, "id") else None,
        "name": run.name if hasattr(run, "name") else None,
        "run_type": run.run_type if hasattr(run, "run_type") else None,
        "start_time": (
            str(run.start_time)
            if hasattr(run, "start_time") and run.start_time
            else None
        ),
        "end_time": (
            str(run.end_time) if hasattr(run, "end_time") and run.end_time else None
        ),
        "status": run.status if hasattr(run, "status") else None,
        "error": str(run.error) if hasattr(run, "error") and run.error else None,
        "inputs": run.inputs if hasattr(run, "inputs") else None,
        "outputs": run.outputs if hasattr(run, "outputs") else None,
        "tags": run.tags if hasattr(run, "tags") else None,
    }

    # Calculate execution time if both start and end times are available
    if info["start_time"] and info["end_time"]:
        try:
            start = datetime.fromisoformat(info["start_time"].replace("Z", "+00:00"))
            end = datetime.fromisoformat(info["end_time"].replace("Z", "+00:00"))
            info["execution_time"] = (end - start).total_seconds()
        except (ValueError, TypeError):
            info["execution_time"] = None
    else:
        info["execution_time"] = None

    return info


def get_run_trace(run_id):
    load_dotenv()
    client = Client()

    # Get the main run
    run = client.read_run(run_id)
    # Get all child runs (steps in the trace)
    child_runs = list(client.list_runs(parent_run_id=run_id))

    # For tool_selection runs, get their LLM child runs
    all_child_runs = []
    for child_run in child_runs:
        all_child_runs.append(child_run)
        if child_run.name == "tool_selection":
            # Get nested child runs that are LLM type
            nested_runs = list(client.list_runs(parent_run_id=child_run.id))
            llm_runs = [run for run in nested_runs if run.run_type == "llm"]
            all_child_runs.extend(llm_runs)

    # Sort all runs by start time
    all_child_runs.sort(
        key=lambda run: (
            run.start_time
            if hasattr(run, "start_time") and run.start_time
            else datetime.min
        )
    )

    trace_data = {
        "main_run": extract_run_info(run),
        "child_runs": [extract_run_info(child) for child in all_child_runs],
    }

    return trace_data


def process_trace_data(trace, output_path=None):
    """
    Process trace data to extract action representations and save them to file if output path is provided.

    Args:
        trace: The trace data returned by get_run_trace()
        output_path: Optional path to save the action representations

    Returns:
        List of action representation strings
    """
    full_action_repr = []

    # Print main run summary
    print(f"\n{'='*50}")
    print(f"Main Run: {trace['main_run']['name']} (ID: {trace['main_run']['id']})")
    print(f"Status: {trace['main_run']['status']}")
    print(f"Total steps: {len(trace['child_runs'])}")
    print(f"{'='*50}")

    # Print each step (child run) in the trace as a summary
    print(f"\nTrace Steps Summary:\n")
    for i, child in enumerate(trace["child_runs"], 1):
        exec_time = (
            f"{child['execution_time']:.3f}s" if child["execution_time"] else "N/A"
        )
        # print(
        #     f"{i}. {child['name']} ({child['run_type']}) - {child['status']} - {exec_time}"
        # )

        if child["name"] == "tool_selection":
            tool_call = child["inputs"]["tool_calls"][0]
            print(f"Action picked through tool call: {child['inputs']['tool_calls']}")

        if child["name"] == "ChatOpenAI" and tool_call.get("name") == "browser_use":
            content = child["inputs"]["messages"][0][0]["kwargs"]["content"][0]["text"]
            start_marker = "## Clickable elements\nThe clickable elements within the currently selected browser tab.\n\n"
            if start_marker in content:
                elements_section = content.split(start_marker)[1]
                end_pattern = (
                    r"\.\.\. \d+ pixels below - you can scroll to see more \.\.\."
                )
                match = re.search(end_pattern, elements_section)
                if match:
                    elements_section = elements_section[: match.start()].strip()

                    # Parse elements into a dictionary
                    element_dict = {}
                    for line in elements_section.split("\n"):
                        if "[:]" in line:
                            idx, desc = line.split("[:]", 1)
                            if idx != "_":  # Skip non-interactive elements
                                element_dict[idx] = desc.strip()

            # Check if it's a browser_use action with an index
            if (
                tool_call.get("name") == "browser_use"
                and "args" in tool_call
                and "index" in tool_call["args"]
            ):
                index = str(
                    tool_call["args"]["index"]
                )  # Convert index to string since our dict keys are strings
                element_desc = element_dict.get(index, "Description not found")
                action_repr = convert_direct_inputs_to_action_reprs(
                    tool_call, element_desc
                )
                full_action_repr.append(action_repr)
                print(f"Action representation: {action_repr}")

    # Save full details to file if output path provided
    if output_path:
        with open(output_path, "w") as f:
            for action in full_action_repr:
                if action is not None:
                    f.write(action + "\n")
        print(f"Full action_repr saved to {output_path}")

    return full_action_repr


def main():
    parser = argparse.ArgumentParser(
        description="Read LangSmith trace for a given run ID"
    )
    parser.add_argument("run_id", help="The run ID to fetch trace for")
    parser.add_argument("--output", "-o", help="Output file path (optional)")
    args = parser.parse_args()

    trace = get_run_trace(args.run_id)
    process_trace_data(trace, args.output)


if __name__ == "__main__":
    main()
