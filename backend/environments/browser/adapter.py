import logging
from typing import Dict, Any, Optional
import json

from browser_use.browser.browser import Browser, BrowserConfig
from browser_use.browser.context import BrowserContext, BrowserContextWindowSize
from core.interfaces import BaseEnvironment, SharedContext, BaseEnvironmentState
from graph.nodes import EnvironmentOutput
from src.browser.custom_browser import CustomBrowser
from src.browser.custom_context import BrowserContextConfig
from core.tools import ToolRegistry
from .tools import register_browser_tools
from src.controller.custom_controller import CustomController
from browser_use import ActionModel

logger = logging.getLogger(__name__)


class BrowserEnvironmentAdapter(BaseEnvironment):
    """Adapts browser_use browser management to LangGraph environment interface"""

    def __init__(self):
        self.browser: Optional[CustomBrowser] = None
        self.browser_context: Optional[BrowserContext] = None
        self.tool_registry = ToolRegistry()
        self._state = BaseEnvironmentState(status="initialized")
        register_browser_tools(self.tool_registry)
        self.controller = CustomController()
        logger.info("Initializing BrowserEnvironmentAdapter")

    async def initialize(self, context: SharedContext) -> None:
        """Initialize browser with settings from context"""
        logger.info("Starting browser initialization")
        browser_config = self._get_browser_config(context)
        window_size = self._get_window_size(context)

        if not self.browser:
            logger.info("Creating new browser instance")
            self.browser = CustomBrowser(config=browser_config)
            logger.info(f"Browser created: {id(self.browser)}")

        if not self.browser_context:
            logger.info("Creating new browser context")
            self.browser_context = await self.browser.new_context(
                config=BrowserContextConfig(
                    no_viewport=False, browser_window_size=window_size
                )
            )
            logger.info(f"Browser context created: {id(self.browser_context)}")

    async def get_state(self) -> BaseEnvironmentState:
        """Get the current state of the browser environment"""
        is_ready = self.browser is not None and self.browser_context is not None
        self._state.status = "ready" if is_ready else "not_ready"
        return self._state

    async def execute(self, action: Dict[str, Any]) -> EnvironmentOutput:
        """Execute browser action and return standardized output"""
        logger.info(
            f"Execute called with browser_context id: {id(self.browser_context)}"
        )
        self._state.status = "executing"
        try:
            if not self.browser_context:
                raise RuntimeError("Browser context not initialized")

            if "action" in action:
                logger.info(
                    f"Processing action sequence: {json.dumps(action['action'], indent=2)}"
                )

                action_models = []
                for raw_action in action["action"]:
                    logger.info(f"Raw action: {raw_action}")

                    # Create ActionModel directly with the raw action
                    # Don't modify the structure - pass it through as-is
                    model_class = self.controller.registry.create_action_model()
                    action_model = model_class.model_validate(raw_action)

                    logger.info(
                        f"Created ActionModel: {action_model.model_dump_json()}"
                    )
                    action_models.append(action_model)

                # Execute actions
                logger.info(
                    f"Calling multi_act with browser_context id: {id(self.browser_context)}"
                )
                results = await self.controller.multi_act(
                    action_models, self.browser_context
                )
                logger.info(
                    f"Multi_act complete. Results: {[r.model_dump() for r in results]}"
                )

                # Process results
                success = all(not r.error for r in results)
                error = next((r.error for r in results if r.error), None)

                return EnvironmentOutput(
                    success=success,
                    result={"action_results": [r.model_dump() for r in results]},
                    error=error,
                )

            else:
                # Legacy single action handling
                logger.info(f"Processing single action: {json.dumps(action, indent=2)}")
                result = await self._execute_browser_action(action)
                logger.info(f"Single action result: {result}")
                return EnvironmentOutput(
                    success=True, result={"action_result": result}, error=None
                )

        except Exception as e:
            self._state.status = "error"
            self._state.error = str(e)
            logger.error(f"Browser action failed: {str(e)}")
            return EnvironmentOutput(success=False, error=str(e))
        finally:
            self._state.status = "ready"

    def can_handle_action(self, action: Dict[str, Any]) -> bool:
        """Determine if action is a browser action using tool registry"""
        action_type = next(iter(action.keys())) if action else None
        if not action_type:
            return False

        tool_metadata = self.tool_registry.get_metadata(action_type)
        return tool_metadata is not None and tool_metadata.requires_browser

    async def cleanup(self) -> None:
        """Clean up browser resources"""
        if self.browser_context:
            await self.browser_context.close()
            self.browser_context = None
        if self.browser:
            await self.browser.close()
            self.browser = None

    def _get_browser_config(self, context: SharedContext) -> BrowserConfig:
        """Extract browser config from shared context"""
        return BrowserConfig(
            headless=context.global_memory.get("headless", True),
            disable_security=context.global_memory.get("disable_security", False),
        )

    def _get_window_size(self, context: SharedContext) -> BrowserContextWindowSize:
        """Get window size from context"""
        return BrowserContextWindowSize(
            width=context.global_memory.get("window_w", 1280),
            height=context.global_memory.get("window_h", 720),
        )

    async def _execute_browser_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute browser action using existing controller pattern"""
        if not self.browser_context:
            raise RuntimeError("Browser context not initialized")

        # Convert to ActionModel format expected by controller
        action_model = self.controller.registry.create_action_model()(**action)

        # Use existing controller execution path
        result = await self.controller.act(action_model, self.browser_context)

        return {
            "result": result.extracted_content if result else None,
            "error": result.error if result else None,
        }
