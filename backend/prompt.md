# Action Engine Architecture

## Current Approach

We are simplifying the agent architecture to follow a clear, linear flow:

```
Start -> Executor -> End
```

This represents the minimal viable flow to test tool usage and basic agent functionality.

## Target Architecture

The target architecture will evolve to:

```
Start -> Planning (ReAct) -> Executor (Tool-use) -> End
```

### Component Responsibilities

1. **Planning Node (ReAct)**

   - Analyzes the task
   - Determines required actions
   - Creates structured execution plan

2. **Executor Node**
   - Handles tool interaction
   - Executes planned actions
   - Returns action results

This simplified architecture removes the complexity of multiple environment handlers and coordinators, focusing on a clear planning-execution cycle.
