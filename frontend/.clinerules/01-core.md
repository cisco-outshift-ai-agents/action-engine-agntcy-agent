# Core Rules for Action Engine Frontend

## Project Overview

This is the frontend application for Action Engine, built with React, TypeScript, and Vite. It provides an interactive and collaborative interface for executing and managing multi-environment agentic operations.

## Key Technologies

- React 18+ with TypeScript
- Vite for build tooling
- Tailwind CSS for styling
- VNC for remote desktop interaction
- State management using stores

## Code Organization

### Component Structure

- Components should be organized by feature/domain in `src/components/`
- Shared UI components belong in `src/components/ui/`
- Page components should be placed in `src/pages/`
- We have imported chat components from a previous project which are located under the `src/components/newsroom` directory. This is for the styling of the chat UX.

### TypeScript Guidelines

- Use TypeScript for all new code
- Define interfaces/types in dedicated type files (e.g., `types.ts`)
- Prefer explicit type annotations over `any`
- Use proper TypeScript features like generics, unions, and intersections when appropriate

### State Management

- Use stores for global state management
- Keep component state local when possible
- Follow immutability patterns for state updates

## Styling Conventions

- Use Tailwind CSS for styling
- Custom CSS should be minimal and placed in `src/styles/`
- Follow responsive design principles
- Maintain consistent spacing and layout patterns

## Component Guidelines

1. Function Components

   - Use function components with hooks
   - Implement proper error boundaries
   - Follow React best practices for performance

2. Props

   - Define prop interfaces for all components
   - Use sensible defaults where appropriate
   - Document complex props

3. Effects

   - Minimize use of effects
   - Clean up subscriptions and event listeners
   - Handle async operations properly

## Error Handling

- Implement proper error boundaries
- Use try/catch blocks for async operations
- Provide user-friendly error messages
- Log errors appropriately

## Performance Considerations

- Implement proper memoization where needed
- Avoid unnecessary re-renders
- Optimize asset loading and bundling
- Use proper React patterns (useMemo, useCallback) when appropriate

## Testing

- Write unit tests for critical functionality
- Test both success and error paths
- Mock external dependencies appropriately

## File Naming Conventions

- Use kebab-case for file names
- Component files should match their component name
- Use `.tsx` extension for React components
- Use `.ts` extension for pure TypeScript files

## Import/Export Guidelines

- Use named exports by default
- Group imports by type (React, third-party, local)
- Avoid circular dependencies
- Use relative paths for local imports

## Version Control

- Write meaningful commit messages
- Keep PRs focused and reasonably sized
- Update documentation when making significant changes

## Build and Development

- Use `npm` as the package manager
- Follow semantic versioning
- Keep dependencies up to date
- Document any special build requirements

## Documentation

- Document complex business logic
- Include inline comments for non-obvious code
- Update README.md for significant changes
- Document environment variables and configuration
