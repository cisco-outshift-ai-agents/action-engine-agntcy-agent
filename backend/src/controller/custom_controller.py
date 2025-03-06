import asyncio
import logging
from typing import Optional, Type

from browser_use import ActionModel
import pyperclip
from browser_use.agent.views import ActionResult
from browser_use.browser.context import BrowserContext
from src.terminal.terminal_views import TerminalCommandAction
from src.terminal.terminal_manager import TerminalManager
from browser_use.controller.service import Controller
from pydantic import BaseModel
from browser_use.utils import time_execution_async, time_execution_sync

logger = logging.getLogger(__name__)

class CustomController(Controller):
    def __init__(
        self,
        exclude_actions: list[str] = [],
        output_model: Optional[Type[BaseModel]] = None,
 ):
        super().__init__(exclude_actions=exclude_actions, output_model=output_model)
        self._register_custom_actions()

    def _register_custom_actions(self):
        """Register all custom browser actions"""

        @self.registry.action("Copy text to clipboard")
        def copy_to_clipboard(text: str):
            pyperclip.copy(text)
            return ActionResult(extracted_content=text)

        @self.registry.action("Paste text from clipboard", requires_browser=True)
        async def paste_from_clipboard(browser: BrowserContext):
            text = pyperclip.paste()
            # send text to browser
            page = await browser.get_current_page()
            await page.keyboard.type(text)

            return ActionResult(extracted_content=text)

        @self.registry.action('Execute a command in terminal', param_model=TerminalCommandAction)
        async def execute_terminal_command(params: TerminalCommandAction) -> ActionResult:
            """Execute a command in the terminals"""
            try:
                terminal_manager = TerminalManager()

                # Try to get an active terminal
                terminal_id = await terminal_manager.get_current_terminal_id()
                
                output, success = await terminal_manager.execute_command(terminal_id, params.command)
                if not success:
                    logger.error(f"Command execution failed: {output}")
                    error_msg = f"Command execution failed: {output}"
                    return ActionResult(error=error_msg, include_in_memory=True)
                
                # Execution was successful, get terminal info
                terminal_id = await terminal_manager.get_current_terminal_id() 
                try:
                   terminal_state = await terminal_manager.get_terminal_state(terminal_id)

                   #Format output
                   formatted_output = f"📂={terminal_state['working_directory']}\n\nOutput:\n{output}"
                   return ActionResult(
                       extracted_content=formatted_output,
                       include_in_memory=True
                   )
                except ValueError as e:
                    logger.warning(f"Error getting terminal state: {str(e)}")
                    return ActionResult(extracted_content=output, include_in_memory=True)
            
            except Exception as e:
                error_msg = f"Execution failed: {str(e)}"
                logger.error(error_msg)
                formatted_output = formatted_output

                return ActionResult(extracted_content=formatted_output, include_in_memory=True)

    @time_execution_async('--multi-act')
    async def multi_act(
        self, actions: list[ActionModel], browser_context: Optional[BrowserContext] = None, check_for_new_elements: bool = True
 ) -> list[ActionResult]:
        """Execute multiple actions - supports both browser and terminal actions"""
        results = []

        has_terminal_actions = any("execute_terminal_command" in action.model_dump(exclude_unset=True).keys() for action in actions)

        # Initialize cached path hashes for browser actions if browser_context is provided and it's not terminal actions
        cached_path_hashes = set()
        if browser_context is not None and not has_terminal_actions:
            try:
                session = await browser_context.get_session()
                cached_selector_map = session.cached_state.selector_map
                cached_path_hashes = set(e.hash.branch_path_hash for e in cached_selector_map.values())
                await browser_context.remove_highlights()
            except Exception as e:
                logger.error(f"Error initializing cached path hashes: {str(e)}")

        for i, action in enumerate(actions):
            # Determine action type
            action_data = action.model_dump(exclude_unset=True)
            action_name = next(iter(action_data.keys()), None)
            is_terminal_action = action_name == "execute_terminal_command"
    
            # For browser actions, check element state if needed
            if browser_context and not is_terminal_action and action.get_index() is not None and i != 0:
                try:
                    new_state = await browser_context.get_state()
                    new_path_hashes = set(e.hash.branch_path_hash for e in new_state.selector_map.values())
                    if check_for_new_elements and not new_path_hashes.issubset(cached_path_hashes):
                        # next action requires index but there are new elements on the page
                        logger.info(f'Something new appeared after action {i} / {len(actions)}')
                        break
                except Exception as e:
                    logger.error(f"Error checking element state: {str(e)}")
                   
            try:
                # Execute action based on its type
                if is_terminal_action:
                    # Terminal actions don't need browser_context
                    result = await self.act(action, None)
                    results.append(result)
                    logger.info(f"Terminal action result: {result}")
                else:
                    # Browser actions need browser_context
                    if browser_context is None:
                        results.append(ActionResult(
                            error=f"Browser context required for action: {action_name}",
                            include_in_memory=True
 ))
                        continue
                    results.append(await self.act(action, browser_context))
            except Exception as e:
                logger.error(f"Error executing action {i + 1}: {str(e)}")
                results.append(ActionResult(error=str(e), include_in_memory=True))

            logger.debug(f'Executed action {i + 1} / {len(actions)}')
            if results[-1].is_done or results[-1].error or i == len(actions) - 1:
                break

            # Wait between actions if we have a browser context
            if browser_context:
                await asyncio.sleep(browser_context.config.wait_between_actions)
        return results

    @time_execution_sync('--act')
    async def act(self, action: ActionModel, browser_context: Optional[BrowserContext] = None) -> ActionResult:
        """Execute an action - supports both browser and terminal actions"""
        try:
            for action_name, params in action.model_dump(exclude_unset=True).items():
                if params is not None:
                    # Check if this is a terminal action
                    if action_name == "execute_terminal_command":
                        # Terminal commands don't need browser_context
                        result = await self.registry.execute_action(action_name, params)
                    else:
                        # Browser actions need browser_context
                        if browser_context is None:
                            return ActionResult(
                                error=f"Browser context required for action: {action_name}",
                                include_in_memory=True
 )
                        result = await self.registry.execute_action(action_name, params, browser=browser_context)
                
                    if isinstance(result, str):
                        return ActionResult(extracted_content=result)
                    elif isinstance(result, ActionResult):
                        return result
                    elif result is None:
                        return ActionResult()
                    else:
                        raise ValueError(f'Invalid action result type: {type(result)} of {result}')
            return ActionResult()
        except Exception as e:
            logger.error(f"Error in act method: {str(e)}")
            return ActionResult(error=str(e), include_in_memory=True)
