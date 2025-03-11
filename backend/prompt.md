# Agent Task Prompt for ActionEngine Rewrite

### Primary Objective

You are tasked with implementing a sophisticated multi-environment agent system using LangGraph. This system needs to handle browser automation, code writing, and terminal operations while maintaining clean separation of concerns.

### Context

The codebase is a Python FastAPI application that needs to be restructured to use LangGraph for better state management and environment delegation. The current implementation mixes concerns and doesn't properly separate tool usage.

### Technical Requirements

1. **Architecture Pattern**

- Implement environment delegation pattern using LangGraph's StateGraph
- Each environment (Browser, Code, Terminal) should be isolated
- Tools should be properly defined using Pydantic models
- State transitions must be explicit and typed

2. **Core Components**

- Environment Delegator for routing between environments
- Base Environment interface that all environments must implement
- Standardized tool registration system
- State management system that preserves context across environments

3. **Implementation Guidelines**

```python
# Example state structure
{
    "current_env": "browser",
    "task_description": "Navigate to github.com and create a new repository",
    "execution_history": [],
    "shared_context": {},
    "environment_specific_state": {}
}
```

### Task Sequence

1. Start with the base environment interface and delegator
2. Implement browser environment first (highest priority)
3. Add code environment
4. Add terminal environment
5. Implement state transition validation
6. Add WebSocket integration

### Code Standards

- Use type hints throughout
- Document all public interfaces
- Include error handling at each layer
- Write unit tests for each component
- Follow PEP 8 style guide

### Initial Files to Create

Please create these files in order:

1. `core/interfaces.py`
2. `core/delegator.py`
3. `environments/base.py`
4. `environments/browser/environment.py`
5. `graph/nodes.py`

### Working Notes

- The todo.md file contains the full task breakdown
- Existing code in main.py shows the current WebSocket implementation
- Browser automation uses Playwright
- LangGraph should handle all state transitions

### Success Criteria

- Clean separation between environments
- Type-safe state transitions
- Proper error handling and recovery
- Backward compatible with existing frontend
- Comprehensive test coverage

Would you like to begin with implementing any specific component from this list?

Remember to:

1. Request clarification if any requirements are unclear
2. Comment your code thoroughly
3. Consider edge cases in your implementation
4. Follow established Python best practices
5. Write tests alongside implementation

Ready to start development on any component you choose. Please let me know which part you'd like to tackle first.
