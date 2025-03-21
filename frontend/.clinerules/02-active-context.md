# Active Context: ActionEngine Frontend

This is the frontend application for Action Engine, built with React, TypeScript, and Vite. It provides an interactive and collaborative interface for executing and managing multi-environment agentic operations.

## Current State

### Implementation Status

1. Langgraph transition

   - Status: [In Progress]
   - Branch: [agentify]
   - Components:
   -
   - Key Features:
     - Adds Langgraph support for agentic communication and tool calling

2. Terminal support

   - Status: [In progress]
   - Branch: [terminal-implementation]
   - Components:
   - TODO
   - Key Features:
   - Use a combination of Xterm on the frontend and tmux on the backend to allow the agent to create and modify arbitrary amounts of terminal sessions.

3. Learning support

   - Status: [In progress]
   - Branch: [teaching-observation-support]
   - Components:
   - TODO
   - Key Features:
   - Use Javascript event listening in order to build a model of the user's behavior and use that to teach the agent how to perform tasks.
   - Integrate with the "planning" step of the agent to allow the agent to take in that initial learning state from the user.
