# Active Context: ActionEngine Backend

This document outlines the active work context for the ActionEngine backend system.

The backend system is responsible for executing agent operations, managing state transitions, and orchestrating tool executions.
This system powers a comprehensive agentic browser/terminal/code-use system called ActionEngine. ActionEngine is unique in the sense that it is tailored towards a network engineer persona by providing primitives for "teaching" multi-environment agents specific tasks.
As the agent learns via generated workflows, it becomes more adept at handling complex tasks. This backend system is the core of the ActionEngine system and is responsible for managing all aspects of the generative AI agentic process.

## Current State

### Implementation Status

1. Langgraph transition

   - Status: [In Progress]
   - Branch: [agentify]
   - Components:
     - [graph.py]
     - [tools]
     - [nodes]
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
