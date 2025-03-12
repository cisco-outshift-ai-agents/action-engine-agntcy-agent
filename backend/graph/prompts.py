import json
from typing import List


def format_message_history(messages: list) -> str:
    """Format message history into a narrative prompt"""
    if not messages:
        return ""

    formatted = [
        "Here is the summary of all previous actions taken by AI agents before you:"
    ]

    for i, msg in enumerate(messages, 1):
        state = msg.get("current_state", {})
        # Get action from the state itself since it's stored in response.action
        action = state.get("action", [{}])[0] if state.get("action") else {}

        formatted.append(f"\n## Run {i}")
        formatted.append(f"**Thought**: \"{state.get('thought', '')}\"")
        formatted.append(f"**Action**: {json.dumps(action, indent=2)}")

    return "\n".join(formatted)


CHAIN_OF_THOUGHT_PROMPT = """
You are an agent that can think and plan ahead for a browser/code/terminal automation task.

Another agent will have access to: 
  1. A terminal
  2. A code editor
  3. A browser

Given the following task, and context, generate a series of actions that the agent should take to complete the task.
Format your response like a markdown TODO list.

You will be given 3 pieces of information: 

1. The task provided by the user to be completed
2. The history of the agent's attempts to complete the task (optional)
3. The existing TODO list which you can then edit, append to, or remove items from as you see fit.

## Task
{task}

## Context (Optional)
{context}

## 
{todo_list}
"""


def get_chain_of_thought_prompt(task: str, context: str, todo_list: str) -> str:
    """Generate chain of thought prompt with current context"""

    return CHAIN_OF_THOUGHT_PROMPT.format(
        task=task, context=context, todo_list=todo_list
    )


ROUTER_PROMPT = """You are an expert at breaking down tasks and determining the best environment to execute them.

You will be provided with a todo list and a task to complete.
Based on the task and the todo list, you will need to determine the best environment to complete the task.

Available environments:
- browser: For web automation, form filling, navigation
- terminal: For file system operations, running commands
- code: For code writing, editing, and execution

Given the task and the todo list, determine the best environment to complete the task and provide a reasoning for your choice.

## Task
{task}

## Todo List
{todo_list}
"""


def get_router_prompt(task: str, todo_list: str) -> str:
    """Generate router prompt with task and todo list"""

    return ROUTER_PROMPT.format(task=task, todo_list=todo_list)
