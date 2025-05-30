# ActionEngine Backend

This document outlines the coding standards and best practices for the ActionEngine backend system. The backend system is responsible for executing agent operations, managing state transitions, and orchestrating tool executions.
This system powers a comprehensive agentic browser/terminal/code-use system called ActionEngine. ActionEngine is unique in the sense that it is tailored towards a network engineer persona by providing primitives for "teaching" multi-environment agents specific tasks.
As the agent learns via generated workflows, it becomes more adept at handling complex tasks. This backend system is the core of the ActionEngine system and is responsible for managing all aspects of the generative AI agentic process.

### Agent System Architecture

- Implement nodes as isolated, single-responsibility components
- Use typed state management for all agent operations
- Maintain clear separation between node logic and tool execution
- Document state transitions and decision points
- Implement proper error recovery in agent loops
- Keep agent prompts in separate configuration files
- Version control prompt templates alongside code
- Log all state transitions for debugging

### Code Style and Organization

- Use clear, descriptive names for nodes, tools, and state keys
- Place node-specific logic in dedicated node classes
- Keep tool methods focused on single operations
- Organize imports into standard library, third-party, and local groups
- Use consistent method ordering in classes (lifecycle -> public -> private)
- Include type hints for all public methods and functions
- Follow naming conventions (PascalCase for classes, snake_case for methods)
- Maintain consistent error message formatting
- Use descriptive variable names that indicate type and purpose
- Include docstrings with examples for complex operations
- Use Black for code formatting
- Use isort for import sorting

### Type Safety

- Use strict typing for all function parameters and return values
- Define custom types for complex data structures
- Use TypeVar for generic type implementations
- Leverage type aliases for common patterns
- Document type constraints and assumptions
- Use Protocol classes for interface definitions
- Validate runtime type correctness for external data

### State Management

- Use Pydantic models for state validation
- Implement immutable state patterns where possible
- Document state shape and transitions
- Validate state integrity between node transitions
- Handle edge cases in state mutations
- Implement proper state cleanup on errors
- Use type-safe state access patterns
- Keep state scoped to relevant components

### Async Patterns

- Use proper async/await patterns throughout
- Handle async cleanup in context managers
- Implement timeout mechanisms for long-running operations
- Use asyncio primitives appropriately
- Maintain clear async boundaries between components
- Document concurrent access patterns
- Handle task cancellation gracefully
- Implement proper resource cleanup

- Keep entry point files minimal, serving only as entrypoints
- Organize code into logical modules/packages/directories
- Keep files under 300 lines by splitting into multiple files
- Group small utility functions in utility modules
- Each exported function/method requires detailed documentation comments
- Format code according to language standards before committing
- Make frequent, small git commits while coding to create recovery points
- Use git checkout [commit-hash] -- path/to/file to recover accidentally deleted code
- Group imports according to language-specific best practices
- Break up large modules into multiple files with clear responsibilities

### Project Structure

### Tool System Design

- Keep tool implementations isolated and testable
- Implement proper tool validation and error handling
- Document tool signatures and expected outputs
- Version control tool configurations
- Implement proper retry logic for flaky tools
- Cache tool results where appropriate
- Sanitize tool inputs and outputs
- Log all tool executions for auditing

- Define key components in the README.md
- Separate core logic from UI and data layers
- Place documentation in docs/
- Configuration in config/
- Unit tests alongside the code they test
- Integration tests in separate test/ directory

### Logging Best Practices

- Use structured logging
- Initialize logger at appropriate scope
- Use appropriate log levels (debug, info, warn, error)
- Include context with log entries
- When viewing logs:
  - Always use appropriate flags to limit log output
  - Never use follow/tail flags in scripts as these commands never return
  - Use reasonable log size limits

### Documentation Standards

- Document all public functions, classes, and modules
- Use consistent formatting for comments
- Include examples for complex functions
- Keep README.md up to date with usage instructions
- Document configuration options and their effects
- Create CONTRIBUTING.md for collaboration guidelines

### Error Handling

- Always check error returns
- Provide context when propagating errors
- Use appropriate error types for domain-specific errors
- Include appropriate logging with error context
- Return/throw early on errors to avoid deep nesting
- Consider implementing custom error types when appropriate

### Performance Considerations

- Use profiling tools for optimization
- Benchmark before and after optimizations
- Consider memory usage for large data structures
- Implement pooling for frequently allocated objects
- Use concurrency or parallelism appropriately
- Be aware of garbage collection impact where applicable
- Implement appropriate locking for shared resources

### Security Practices

- Validate all user inputs
- Use prepared statements for database queries
- Implement proper authentication and authorization
- Follow the principle of least privilege
- Keep dependencies updated
- Scan for vulnerabilities regularly
- Avoid hard-coded secrets
