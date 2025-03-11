from core.tools import ToolMetadata, ToolRegistry
from src.controller.custom_controller import CustomController


def register_browser_tools(registry: ToolRegistry) -> None:
    """Register browser tools using existing controller actions"""
    controller = CustomController()

    # Map existing controller actions to new tool registry
    # First get available actions (different controllers might store actions differently)
    available_actions = {}

    # Try different common attribute names used in Registry implementations
    if hasattr(controller.registry, "actions"):
        available_actions = controller.registry.actions
    elif hasattr(controller.registry, "tools"):
        available_actions = controller.registry.tools
    elif hasattr(controller.registry, "_registry"):
        available_actions = controller.registry._registry
    else:
        # Fallback to getting all callable attributes that don't start with _
        available_actions = {
            name: getattr(controller.registry, name)
            for name in dir(controller.registry)
            if callable(getattr(controller.registry, name))
            and not name.startswith("_")
            and name not in ("register", "get", "list")
        }

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
