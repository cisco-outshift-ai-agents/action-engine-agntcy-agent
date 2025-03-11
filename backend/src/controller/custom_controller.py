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
        logger.info("Initializing CustomController")
        super().__init__(exclude_actions=exclude_actions, output_model=output_model)
        logger.info("Registering custom actions")
        self._register_custom_actions()

        # Log available actions safely
        try:
            actions = self._get_registry_actions()
            logger.info(f"Available actions: {list(actions)}")
        except Exception as e:
            logger.warning(f"Could not list available actions: {e}")

    def _get_registry_actions(self):
        """Get all registered actions from registry"""
        if hasattr(self.registry, "_registry"):
            return self.registry._registry.keys()
        elif hasattr(self.registry, "_actions"):
            return self.registry._actions.keys()
        return []

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

        @self.registry.action(
            "Execute a command in terminal", param_model=TerminalCommandAction
        )
        async def execute_terminal_command(
            params: TerminalCommandAction,
        ) -> ActionResult:
            """Execute a command in the terminals"""
            try:
                terminal_manager = TerminalManager()

                # Try to get an active terminal
                terminal_id = await terminal_manager.get_current_terminal_id()

                output, success = await terminal_manager.execute_command(
                    terminal_id, params.command
                )
                if not success:
                    logger.error(f"Command execution failed: {output}")
                    error_msg = f"Command execution failed: {output}"
                    return ActionResult(error=error_msg, include_in_memory=True)

                # Execution was successful, get terminal info
                terminal_id = await terminal_manager.get_current_terminal_id()
                try:
                    terminal_state = await terminal_manager.get_terminal_state(
                        terminal_id
                    )
                    working_directory = terminal_state.get("working_directory", "")
                    # Format output
                    formatted_output = (
                        f"Directory:{working_directory}\n\nOutput:\n{output}"
                    )
                    return ActionResult(
                        extracted_content=formatted_output, include_in_memory=True
                    )
                except ValueError as e:
                    logger.warning(f"Error getting terminal state: {str(e)}")
                    return ActionResult(
                        extracted_content=output, include_in_memory=True
                    )

            except Exception as e:
                error_msg = f"Execution failed: {str(e)}"
                logger.error(error_msg)
                formatted_output = formatted_output

                return ActionResult(
                    extracted_content=formatted_output, include_in_memory=True
                )

    @time_execution_async("--multi-act")
    async def multi_act(
        self,
        actions: list[ActionModel],
        browser_context: Optional[BrowserContext] = None,
        check_for_new_elements: bool = True,
    ) -> list[ActionResult]:
        logger.info(
            f"multi_act called with browser_context id: {id(browser_context) if browser_context else None}"
        )
        logger.info(f"Actions received: {[a.model_dump_json() for a in actions]}")

        results = []

        has_terminal_actions = any(
            "execute_terminal_command" in action.model_dump(exclude_unset=True).keys()
            for action in actions
        )

        # Initialize cached path hashes for browser actions if browser_context is provided and it's not terminal actions
        cached_path_hashes = set()
        if browser_context is not None and not has_terminal_actions:
            try:
                session = await browser_context.get_session()
                cached_selector_map = session.cached_state.selector_map
                cached_path_hashes = set(
                    e.hash.branch_path_hash for e in cached_selector_map.values()
                )
                await browser_context.remove_highlights()
            except Exception as e:
                logger.error(f"Error initializing cached path hashes: {str(e)}")

        for i, action in enumerate(actions):
            action_dump = action.model_dump(exclude_unset=True)
            logger.info(f"Processing action {i}: {action_dump}")

            if not action_dump:
                logger.error(f"Empty action data for action {i}")
                continue

            # Determine action type
            action_data = action.model_dump(exclude_unset=True)
            action_name = next(iter(action_data.keys()), None)
            is_terminal_action = action_name == "execute_terminal_command"

            # For browser actions, check element state if needed
            if (
                browser_context
                and not is_terminal_action
                and action.get_index() is not None
                and i != 0
            ):
                try:
                    new_state = await browser_context.get_state()
                    new_path_hashes = set(
                        e.hash.branch_path_hash for e in new_state.selector_map.values()
                    )
                    if check_for_new_elements and not new_path_hashes.issubset(
                        cached_path_hashes
                    ):
                        # next action requires index but there are new elements on the page
                        logger.info(
                            f"Something new appeared after action {i} / {len(actions)}"
                        )
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
                        results.append(
                            ActionResult(
                                error=f"Browser context required for action: {action_name}",
                                include_in_memory=True,
                            )
                        )
                        continue
                    results.append(await self.act(action, browser_context))
            except Exception as e:
                logger.error(f"Error executing action {i + 1}: {str(e)}")
                results.append(ActionResult(error=str(e), include_in_memory=True))

            logger.debug(f"Executed action {i + 1} / {len(actions)}")
            if results[-1].is_done or results[-1].error or i == len(actions) - 1:
                break

            # Wait between actions if we have a browser context
            if browser_context:
                await asyncio.sleep(browser_context.config.wait_between_actions)
        return results

    @time_execution_sync("--act")
    async def act(
        self, action: ActionModel, browser_context: Optional[BrowserContext] = None
    ) -> ActionResult:
        logger.info(
            f"act called with browser_context id: {id(browser_context) if browser_context else None}"
        )
        logger.info(f"Action data: {action.model_dump_json() if action else 'None'}")

        try:
            logger.info(
                f"Starting action execution with model: {action.model_dump_json()}"
            )
            logger.info(f"Browser context available: {browser_context is not None}")

            action_data = action.model_dump(exclude_unset=True)
            logger.info(f"Action data after dump: {action_data}")

            for action_name, params in action_data.items():
                logger.info(f"Processing action: {action_name} with params: {params}")
                registry_actions = self._get_registry_actions()
                logger.info(f"Registry actions: {list(registry_actions)}")

                if params is not None:
                    # Check if this is a terminal action
                    if action_name == "execute_terminal_command":
                        logger.info("Executing terminal command")
                        result = await self.registry.execute_action(action_name, params)
                    else:
                        # Browser actions need browser_context
                        if browser_context is None:
                            error_msg = (
                                f"Browser context required for action: {action_name}"
                            )
                            logger.error(error_msg)
                            return ActionResult(error=error_msg, include_in_memory=True)

                        logger.info(f"Executing browser action: {action_name}")
                        # Check if action exists in registry's actions
                        registry_actions = (
                            self.registry.registry.actions
                            if hasattr(self.registry, "registry")
                            and hasattr(self.registry.registry, "actions")
                            else {}
                        )
                        logger.info(
                            f"Action registered: {action_name in registry_actions}"
                        )
                        logger.info(
                            f"Browser state: {await browser_context.get_state()}"
                        )

                        try:
                            result = await self.registry.execute_action(
                                action_name, params, browser=browser_context
                            )
                            logger.info(
                                f"Action execution result: {result.model_dump_json() if result else None}"
                            )
                        except Exception as action_error:
                            logger.error(
                                f"Action execution failed: {str(action_error)}",
                                exc_info=True,
                            )
                            return ActionResult(
                                error=str(action_error), include_in_memory=True
                            )

                    if isinstance(result, str):
                        logger.info(f"String result received: {result}")
                        return ActionResult(extracted_content=result)
                    elif isinstance(result, ActionResult):
                        logger.info(
                            f"ActionResult received: {result.model_dump_json()}"
                        )
                        return result
                    elif result is None:
                        logger.info("No result received")
                        return ActionResult()
                    else:
                        error_msg = (
                            f"Invalid action result type: {type(result)} of {result}"
                        )
                        logger.error(error_msg)
                        raise ValueError(error_msg)

            logger.info("No actions executed")
            return ActionResult()

        except Exception as e:
            logger.error(f"Error in act method: {str(e)}", exc_info=True)
            return ActionResult(error=str(e), include_in_memory=True)
