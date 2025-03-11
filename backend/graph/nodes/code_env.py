# class CodeEnvNode:
#     """Handles code environment execution with own planning"""

#     def __init__(self):
#         self.name = "code_env"

#     async def __call__(self, state: AgentState, config: Dict):
#         """Make node callable for LangGraph and ensure async execution"""
#         return await self.ainvoke(state, config)

#     def invoke(self, state: AgentState, config: Dict):
#         """Prevent sync execution"""
#         raise NotImplementedError("Code environment requires async execution")

#     async def ainvoke(self, state: AgentState, config: Dict) -> Dict:
#         """Plan and execute code actions"""
#         llm = config.get("configurable", {}).get("llm")
#         env_registry = config.get("configurable", {}).get("env_registry", {})

#         # Get tools
#         code_env = env_registry.get(EnvironmentType.CODE)
#         if not code_env:
#             return {"error": "Code environment not available"}

#         # Plan next action using available tools
#         tools = code_env.tool_registry.get_openai_functions()

#         messages = [
#             SystemMessage(content="You are a code automation expert"),
#             HumanMessage(
#                 content=f"Task: {state['task']}\nWhat code action should we take next?"
#             ),
#         ]

#         function_call = await llm.ainvoke(messages, functions=tools)

#         # Execute planned action
#         if function_call.additional_kwargs.get("function_call"):
#             tool_name = function_call.additional_kwargs["function_call"]["name"]
#             tool_args = json.loads(
#                 function_call.additional_kwargs["function_call"]["arguments"]
#             )

#             action = {"type": tool_name, "params": tool_args}
#             result = await code_env.execute(action)

#             state["environment_output"] = result.model_dump()
#             if result.error:
#                 state["error"] = result.error

#         return state
