import logging

from core.tools import ToolMetadata, ToolRegistry
from src.controller.custom_controller import CustomController

logger = logging.getLogger(__name__)


def get_registry_actions(controller):
    """Get all registered actions from a controller's registry"""
    try:
        # Try accessing internal _actions dictionary if it exists
        if hasattr(controller.registry, "_actions"):
            return controller.registry._actions
        # Try accessing any _registry attribute
        elif hasattr(controller.registry, "_registry"):
            return controller.registry._registry
        # Fallback: get all callable attributes that don't start with _
        return {
            name: getattr(controller.registry, name)
            for name in dir(controller.registry)
            if callable(getattr(controller.registry, name))
            and not name.startswith("_")
            and name
            not in ("register", "get", "list", "execute_action", "create_action_model")
        }
    except Exception as e:
        logger.error(f"Failed to get registry actions: {e}")
        return {}


def register_browser_tools(registry: ToolRegistry) -> None:
    """Register browser tools using existing controller actions"""
    controller = CustomController()

    # Get available actions using helper function
    available_actions = get_registry_actions(controller)

    # Register available actions
    for action_name, action_func in available_actions.items():
        if callable(action_func):  # Ensure we only register callable items
            registry.register_tool(
                name=action_name,
                tool_func=action_func,
                metadata=ToolMetadata(
                    name=action_name,
                    description=action_func.__doc__ or action_name,
                    requires_browser=True,
                ),
                param_model=(
                    action_func.param_model
                    if hasattr(action_func, "param_model")
                    else None
                ),
            )
