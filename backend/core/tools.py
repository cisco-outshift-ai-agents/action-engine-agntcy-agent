from typing import Any, Callable, Dict, List, Optional, Type
from pydantic import BaseModel, create_model
from core.interfaces import BaseToolRegistry


class ToolMetadata(BaseModel):
    """Metadata for registered tools"""

    name: str
    description: str
    requires_browser: bool = False
    requires_terminal: bool = False
    requires_code: bool = False


class ToolRegistry(BaseToolRegistry):
    """Enhanced tool registry that supports multiple environments"""

    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._metadata: Dict[str, ToolMetadata] = {}
        self._params: Dict[str, Type[BaseModel]] = {}

    def register_tool(
        self,
        name: str,
        tool_func: Callable,
        metadata: ToolMetadata,
        param_model: Optional[Type[BaseModel]] = None,
    ) -> None:
        """Register a tool with metadata and parameter model"""
        self._tools[name] = tool_func
        self._metadata[name] = metadata
        if param_model:
            self._params[name] = param_model

    def get_tool(self, name: str) -> Optional[Callable]:
        """Get a registered tool"""
        return self._tools.get(name)

    def get_metadata(self, name: str) -> Optional[ToolMetadata]:
        """Get metadata for a tool"""
        return self._metadata.get(name)

    def list_tools(self) -> List[str]:
        """List all registered tools"""
        return list(self._tools.keys())

    def get_tools_for_environment(self, env_name: str) -> List[str]:
        """Get tools that can be used in a specific environment"""
        env_tools = []
        for name, metadata in self._metadata.items():
            if (
                (env_name == "browser" and metadata.requires_browser)
                or (env_name == "terminal" and metadata.requires_terminal)
                or (env_name == "code" and metadata.requires_code)
            ):
                env_tools.append(name)
        return env_tools

    def create_action_model(self) -> Type[BaseModel]:
        """Create a Pydantic model for all registered tools"""
        fields = {}
        for name, param_model in self._params.items():
            fields[name] = (Optional[param_model], None)

        return create_model("DynamicActions", **fields, __base__=BaseModel)

    def action(self, name: str, requires_browser: bool = False):
        """Decorator compatibility layer for old-style action registration"""

        def decorator(func: Callable):
            self.register_tool(
                name=name,
                tool_func=func,
                metadata=ToolMetadata(
                    name=name,
                    description=name,  # Can extract from docstring in future
                    requires_browser=requires_browser,
                ),
            )
            return func

        return decorator

    async def execute_action(
        self, action_name: str, params: Any = None, **kwargs
    ) -> Any:
        """Compatibility method for executing actions old-style"""
        tool = self.get_tool(action_name)
        if not tool:
            raise ValueError(f"Unknown action: {action_name}")

        if params is not None:
            return await tool(params, **kwargs)
        return await tool(**kwargs)

    def get_openai_functions(self) -> List[Dict]:
        """Convert tools to OpenAI function format"""
        functions = []
        for name, metadata in self._metadata.items():
            param_model = self._params.get(name)
            functions.append(
                {
                    "name": name,
                    "description": metadata.description,
                    "parameters": (
                        param_model.model_json_schema() if param_model else {}
                    ),
                }
            )
        return functions
