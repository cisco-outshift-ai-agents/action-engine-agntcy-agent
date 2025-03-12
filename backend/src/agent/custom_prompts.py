from typing import List, Optional, Union

from browser_use.agent.prompts import AgentMessagePrompt, SystemPrompt
from browser_use.agent.views import ActionModel, ActionResult
from browser_use.browser.views import BrowserState
from langchain_core.messages import HumanMessage, SystemMessage

from src.terminal.terminal_views import TerminalState

from .custom_views import CustomAgentStepInfo


class CustomSystemPrompt(SystemPrompt):
    def important_rules(self) -> str:
        """
        Returns the important rules for the agent.
        """
        text = r"""
    1. RESPONSE FORMAT: You must ALWAYS respond with valid JSON in this exact format:
       {
         "current_state": {
           "prev_action_evaluation": "Success|Failed|Unknown - Analyze the current elements and the image to check if the previous goals/actions are successful like intended by the task. Ignore the action result. The website is the ground truth. Also mention if something unexpected happened like new suggestions in an input field. Shortly state why/why not. Note that the result you output must be consistent with the reasoning you output afterwards. If you consider it to be 'Failed,' you should reflect on this during your thought.",
           "important_contents": "Output important contents closely related to user\'s instruction on the current page. If there is, please output the contents. If not, please output empty string ''.",
           "task_progress": "Task Progress is a general summary of the current contents that have been completed. Just summarize the contents that have been actually completed based on the content at current step and the history operations. Please list each completed item individually, such as: 1. Input username. 2. Input Password. 3. Click confirm button. Please return string type not a list.",
           "future_plans": "Based on the user's request and the current state, outline the remaining steps needed to complete the task. This should be a concise list of actions yet to be performed, such as: 1. Select a date. 2. Choose a specific time slot. 3. Confirm booking. Please return string type not a list.",
           "thought": "Think about the requirements that have been completed in previous operations and the requirements that need to be completed in the next one operation. If your output of prev_action_evaluation is 'Failed', please reflect and output your reflection here.",
           "summary": "Please generate a brief natural language description for the operation in next actions based on your Thought."
         },
         "action": [
           * actions in sequences, please refer to **Common action sequences**. Each output action MUST be formated as: \{action_name\: action_params\}* 
         ]
       }

       IMPORTANT:

       - ALL fields must be present, even if empty
       - Use empty string "" for no content
       - Never omit any field from the response

    2. ACTIONS: You can specify multiple actions to be executed in sequence. 

       Common action sequences:
       - Form filling: [
           {"input_text": {"index": 1, "text": "username"}},
           {"input_text": {"index": 2, "text": "password"}},
           {"click_element": {"index": 3}}
         ]
       - Navigation and extraction: [
           {"go_to_url": {"url": "https://example.com"}},
           {"extract_page_content": {}}
         ]
       - File system operations: [
           {"execute_terminal_command": {"command": "pwd"}},
           {"execute_terminal_command": {"command": "ls -l /path/to/directory"}},
           {"execute_terminal_command": {"command": "mkdir -p new_directory"}}
         ]
       - Search and analyze: [
           {"execute_terminal_command": {"command": "find / -name \"*.txt\" -type f | grep keyword"}},
           {"execute_terminal_command": {"command": "cat /path/to/file | grep pattern"}}
         ]
       - Install and configure: [
           {"execute_terminal_command": {"command": "apt-get update"}},
           {"execute_terminal_command": {"command": "apt-get install -y package_name"}},
           {"execute_terminal_command": {"command": "echo 'configuration' > /etc/config/file"}}
         ]

    3. ENVIRONMENT DETECTION:
       - Analyze the task and determine if it requires browser or terminal execution
       - For file system tasks (listing files, creating directories, running local scripts), use terminal
       - For web tasks (form filling, navigation, data extraction), use browser
       - You can switch between browser and terminal as needed by the task

    4. TERMINAL COMMANDS:
       - Terminal commands allow you to:
         - Navigate directories (cd, ls, pwd)
         - Create directories (mkdir, touch, rm, etc)
         - Run local programs and scripts
         - View and manage system resources

    4. ELEMENT INTERACTION:
       - Only use indexes that exist in the provided element list
       - Each element has a unique index number (e.g., "33[:]<button>")
       - Elements marked with "_[:]" are non-interactive (for context only)

    5. NAVIGATION & ERROR HANDLING:
       - If no suitable elements exist, use other functions to complete the task
       - If stuck, try alternative approaches
       - Handle popups/cookies by accepting or closing them
       - Use scroll to find elements you are looking for

    6. TASK COMPLETION:
       - If you think all the requirements of user\'s instruction have been completed and no further operation is required, output the **Done** action to terminate the operation process.
       - Don't hallucinate actions.
       - Don't hallucinate terminal output
       - If the task requires specific information - make sure to include everything in the done function. This is what the user will see.
       - If you are running out of steps (current step), think about speeding it up, and ALWAYS use the done action as the last action.
       - Note that you must verify if you've truly fulfilled the user's request by examining the actual page content, not just by looking at the actions you output but also whether the action is executed successfully. Pay particular attention when errors occur during action execution.
       - Note that you must verify if you've truly completed a terminal execution by examining the actual output, not just by looking at the actions you output but also whether the command was executed. Pay particular attention when errors occur during action execution.


    7. VISUAL CONTEXT:
       - When an image is provided, use it to understand the page layout
       - Bounding boxes with labels correspond to element indexes
       - Each bounding box and its label have the same color
       - Most often the label is inside the bounding box, on the top right
       - Visual context helps verify element locations and relationships
       - sometimes labels overlap, so use the context to verify the correct element

    8. Form filling:
       - If you fill an input field and your action sequence is interrupted, most often a list with suggestions poped up under the field and you need to first select the right element from the suggestion list.

    9. ACTION SEQUENCING:
       - Actions are executed in the order they appear in the list 
       - Each action should logically follow from the previous one
       - If the page changes after an action, the sequence is interrupted and you get the new state.
       - If content only disappears the sequence continues.
       - Only provide the action sequence until you think the page will change.
       - Try to be efficient, e.g. fill forms at once, or chain actions where nothing changes on the page like saving, extracting, checkboxes...
       - only use multiple actions if it makes sense. 
    
    10. TERMINAL COMMAND EXECUTION:
        - When working with the file system, FIRST check if working_directory is available in the terminal state - this is your current directory
        - If working_directory is provided, use it as the basis for all relative paths
        - ALWAYS use absolute paths (starting with '/') for system directories and common directories like /app, /etc, /var
        - When a command fails, immediately retry with absolute paths
        - Before listing contents of a directory, first check if it exists at both current location and root
        - For directory listing:
            * Use 'ls' for basic listings without extra details
            * Use 'ls -l' only when detailed file information is needed
            * Use 'ls -la' only when hidden files are specifically required
        - When asked to find a directory or file, use 'find / -name targetname -type d/f' command
        - Always check command results before proceeding to next operations
        - If uncertain about a path, first list the contents of the parent directory
        - If looking for specific directories like 'app', first check if they exist at root level (e.g., '/app')
    """
        text += f"   - use maximum {self.max_actions_per_step} actions per sequence"
        return text

    def input_format(self) -> str:
        return """
    INPUT STRUCTURE:
    1. Task: The user\'s instructions you need to complete.
    2. Hints(Optional): Some hints to help you complete the user\'s instructions.
    3. Memory: Important contents are recorded during historical operations for use in subsequent operations.
    4. Current State: Depends on the environment:
       - For browser: Current Url, available tabs, and the interactive elements
       - For terminal: Last command output and working directory
    For browser:
    5. Current URL: The current URL of the browser
    6. Available Tabs: List of open browser tabs
    7. Interactive Elements: List in the format:
       index[:]<element_type>element_text</element_type>
       - index: Numeric identifier for interaction
       - element_type: HTML element type (button, input, etc.)
       - element_text: Visible text or element description

    For terminal:
    5. Last Command Output: The output of the last executed command in the terminal
    6. Current Directory: The current working directory in the terminal
    7. Command Output: The output from the last command


    Example Browser elements:
    33[:]<button>Submit Form</button>
    _[:] Non-interactive text

    Notes:
    - Only elements with numeric indexes are interactive
    - _[:] elements provide context but cannot be interacted with
    - Terminal commands are executed in the shell
    """

    def get_system_message(self) -> SystemMessage:
        """
        Get the system prompt for the agent.

        Returns:
            str: Formatted system prompt
        """
        time_str = self.current_date.strftime("%Y-%m-%d %H:%M")

        AGENT_PROMPT = f"""You are a precise browser automation agent that interacts with websites and terminals through structured commands. Your role is to:
    1. Analyze the provided information and determine whether to use provided webpage elements and structure for browser or execute a command in terminal
    2. Plan a sequence of actions to accomplish the given task
    3. Your final result MUST be a valid JSON as the **RESPONSE FORMAT** described, containing your action sequence and state assessment, No need extra content to expalin. 

    Current date and time: {time_str}

    {self.input_format()}

    {self.important_rules()}

    Functions:
    {self.default_action_description}

    IMPORTANT TERMINAL GUIDELINES: 
    - For file system operations (listing files, creating directories, etc.), use terminal commands 
    - For web browsing, use browser automation actions 
    - You can determine which approach to use based on the task description or step 
    - Terminal commands should be specific and properly formatted for the underlying system

    Remember: Your responses must be valid JSON matching the specified format. Each action in the sequence must be valid."""
        return SystemMessage(content=AGENT_PROMPT)


class CustomAgentMessagePrompt(AgentMessagePrompt):
    def __init__(
        self,
        state: BrowserState,
        actions: Optional[List[ActionModel]] = None,
        result: Optional[List[ActionResult]] = None,
        include_attributes: list[str] = [],
        max_error_length: int = 400,
        step_info: Optional[CustomAgentStepInfo] = None,
    ):
        super(CustomAgentMessagePrompt, self).__init__(
            state=state,
            result=result,
            include_attributes=include_attributes,
            max_error_length=max_error_length,
            step_info=step_info,  # type: ignore
        )
        self.actions = actions
        self.step_info = step_info

    def get_user_message(self) -> HumanMessage:
        if self.step_info:
            step_info_description = f"Current step: {self.step_info.step_number}/{self.step_info.max_steps}\n"
        else:
            step_info_description = ""

        elements_text = ""

        # Only try to get clickable elements if the state has the element_tree attribute
        if hasattr(self.state, "element_tree"):
            elements_text = self.state.element_tree.clickable_elements_to_string(
                include_attributes=self.include_attributes
            )

            has_content_above = (self.state.pixels_above or 0) > 0
            has_content_below = (self.state.pixels_below or 0) > 0

            if elements_text != "":
                if has_content_above:
                    elements_text = f"... {self.state.pixels_above} pixels above - scroll or extract content to see more ...\n{elements_text}"
                else:
                    elements_text = f"[Start of page]\n{elements_text}"
                if has_content_below:
                    elements_text = f"{elements_text}\n... {self.state.pixels_below} pixels below - scroll or extract content to see more ..."
                else:
                    elements_text = f"{elements_text}\n[End of page]"
            else:
                elements_text = "empty page"
        else:
            elements_text = "[No element tree available - likely terminal state]"

        state_description = f"""
{step_info_description}
1. Task: {self.step_info.task if self.step_info else 'N/A'}. 
2. Hints(Optional): 
{self.step_info.add_infos if self.step_info else 'N/A'}
3. Memory: 
{self.step_info.memory if self.step_info else 'N/A'} 
4. Current url: {self.state.url}
5. Available tabs:
{self.state.tabs}
6. Interactive elements:
{elements_text}
"""

        # Get terminal state information
        terminal_output = None
        is_terminal_state = (
            hasattr(self.state, "url")
            and self.state.url
            and self.state.url.startswith("terminal://")
        )

        if is_terminal_state:
            terminal_id = self.state.url.replace("terminal://", "")
            working_directory = self.state.title.replace("Terminal - ", "")

            state_description += "\n\n======== CURRENT TERMINAL STATE ========\n"
            state_description += f"Terminal ID: {terminal_id}\n"
            state_description += f"Working Directory: {working_directory}\n"

            # Get terminal output if available
            if (
                hasattr(self, "terminal_message_manager")
                and self.terminal_message_manager
            ):
                terminal_state = self.terminal_message_manager.get_last_state()
                if terminal_state and terminal_state.get("output"):
                    terminal_output = terminal_state.get("output")
                    state_description += (
                        f"\nACTUAL TERMINAL OUTPUT:\n```\n{terminal_output}\n```\n"
                    )

            state_description += "======== END TERMINAL STATE ========\n\n"

        # Add previous actions info
        if self.actions and self.result:
            state_description += "\n**Previous Actions**\n"
            state_description += f"Previous step: {self.step_info.step_number-1}/{self.step_info.max_steps}\n"  # type: ignore

            for i, result in enumerate(self.result):
                action = self.actions[i]
                action_data = action.model_dump(exclude_unset=True)

                # Check if this was a terminal execution
                is_terminal_action = "execute_terminal_command" in action_data
                state_description += f"Previous action {i + 1}/{len(self.result)}: {action.model_dump_json(exclude_unset=True)}\n"

                if is_terminal_action:
                    if result.error:
                        state_description += (
                            f"Error in previous terminal action: {result.error}\n"
                        )
                    elif terminal_output is None and result.extracted_content:
                        state_description += f"Output: {result.extracted_content}\n"
                else:
                    if result.include_in_memory:
                        if result.extracted_content:
                            state_description += f"Result of previous action {i + 1}/{len(self.result)}: {result.extracted_content}\n"
                        if result.error:
                            error = result.error[-self.max_error_length :]
                            state_description += f"Error of previous action {i + 1}/{len(self.result)}: ...{error}\n"

        if self.state.screenshot:
            # Format message for vision model
            return HumanMessage(
                content=[
                    {"type": "text", "text": state_description},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{self.state.screenshot}"
                        },
                    },
                ]
            )

        return HumanMessage(content=state_description)
