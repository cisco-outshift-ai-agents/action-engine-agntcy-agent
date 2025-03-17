import json
from tools.utils import EnvironmentPromptContext
from graph.types import BrainState


def format_message_history(messages: list) -> str:
    """Creates a narrative of previous actions to help the LLM understand context and avoid loops"""
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
    """Builds a prompt that helps the agent plan its next steps based on previous attempts"""
    return CHAIN_OF_THOUGHT_PROMPT.format(
        task=task, context=context, todo_list=todo_list
    )


ROUTER_PROMPT = """You are a router agent that helps determine the best environment for a given task.

You will be provided with a todo list and a task to complete.
Based on the task and the todo list, you will need to determine the best environment to complete the task.

Available environments:
- browser: For web automation, form filling, navigation
- terminal: For file system operations, running commands
- code: For code writing, editing, and execution
- chat: For conversational tasks

Given the task and the todo list, determine the best environment to complete the task and provide a reasoning for your choice.

## Task
{task}

## Todo List
{todo_list}
"""


def get_router_prompt(task: str, todo_list: str) -> str:
    """Helps the agent decide which environment is most appropriate for the current task"""
    return ROUTER_PROMPT.format(task=task, todo_list=todo_list)


PLANNER_PROMPT = """
You are an expert Planning Agent tasked with solving problems efficiently through structured plans.
Your job is:
1. Analyze requests to understand the task scope
2. Create a clear, actionable plan that makes meaningful progress with the `planning` tool
3. Execute steps using available tools as needed
4. Track progress and adapt plans when necessary
5. Use the `terminate` tool to conclude immediately when the task is complete

Please log your responses in the requested JSON format and please always call the `planning` tool to create or update plans as necessary

If the task is complete, use the `terminate` tool to end the task.

Available tools:
- `planning`
- `terminate`
Break tasks into logical steps with clear outcomes. Avoid excessive detail or sub-steps.
Think about dependencies and verification methods.
Know when to conclude - don't continue thinking once objectives are met.
"""


def get_planner_prompt() -> str:
    """Helps the agent understand its role and responsibilities as a planning agent"""
    return PLANNER_PROMPT


ENVIRONMENT_PROMPT = """
Your current working environment has the following state:

## Date
The current date and time.

{current_date}

---

## Terminal windows
The list of all terminal windows and their last performed commands.

{terminal_windows}

---

## Browser tabs
The list of all browser tabs

{browser_tabs}

---

## Current browser information
The current browser tab has this information.

- **URL**: {current_url}
- **Page Title**: {current_page_title}

---

## Clickable elements
The clickable elements within the currently selected browser tab.

{px_above_text}
{clickable_elements}
{px_below_text}
"""


def get_environment_prompt(context: EnvironmentPromptContext) -> str:
    """Helps the agent understand the current state of the environment"""

    px_above_text = (
        f"\n... {context.pixels_above} pixels above - scroll or extract content to see more ..."
        if context.pixels_above
        else ""
    )
    px_below_text = (
        f"\n... {context.pixels_below} pixels below - scroll or extract content to see more ..."
        if context.pixels_below
        else ""
    )

    return ENVIRONMENT_PROMPT.format(
        current_date=context.current_date,
        terminal_windows=context.terminal_windows,
        clickable_elements=context.clickable_elements,
        browser_tabs=context.browser_tabs,
        current_url=context.current_url,
        current_page_title=context.current_page_title,
        px_above_text=px_above_text,
        px_below_text=px_below_text,
    )


THINKING_PROMPT = """
You are an agent that can generate thoughts and ideas to communicate the current state of an 
agentic UI automation workflow to a human user.

You will be provided with the current state of the environment, the state of the conversation, and a generated
plan of how to complete the user's request.  Describe to the user what is happening in the current moment and 
what you plan to do next.

Your output will be viewed by the user, so play the role of a friendly, communicative agent which
clearly describes what the AI is doing and why.  Make your response first-person and friendly.

The previous thoughts are as follows: 

{thought}

"""


def get_thinking_prompt(brainstate: BrainState) -> str:
    """Helps the agent understand its role and responsibilities as a thinking agent"""
    return THINKING_PROMPT.format(
        thought=brainstate.get("thought"),
        important_contents=brainstate.get("important_contents"),
        task_progress=brainstate.get("task_progress"),
        future_plans=brainstate.get("future_plans"),
        summary=brainstate.get("summary"),
        prev_action_evaluation=brainstate.get("prev_action_evaluation"),
    )
