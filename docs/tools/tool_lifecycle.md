# Tool Execution Lifecycle

## 1. Discovery & Prompting
1. The `SupervisorAgent` queries the `ToolRegistry` for available tools.
2. The registry filters tools based on the Agent's `PermissionLevel`.
3. The schemas are formatted into LLM-native function calling definitions and injected into the prompt.

## 2. LLM Evaluation
1. The LLM evaluates if the task requires external data.
2. If yes, it returns one or more `tool_calls` in its response payload.

## 3. Tool Manager Execution
1. The `SupervisorAgent` extracts the `tool_calls` and passes them to the `ToolManager`.
2. `ToolManager` validates permissions again (Defense in Depth).
3. `ToolManager` executes the tool asynchronously, wrapping it in `asyncio.wait_for` based on `timeout_seconds`.
4. If the tool fails (exception), `ToolManager` catches it and applies the `retry_policy` (exponential backoff).
5. Observability metrics (`ToolMetrics`) log the duration, success/failure status, and the agent requesting it.

## 4. Result Synthesis
1. The `ToolManager` wraps outputs in a standard `ToolResult`.
2. The `SupervisorAgent` appends the `ToolResult` into the `AgentState`.
3. The graph routes back to `SupervisorAgent`, which re-prompts the LLM with the newly acquired context.
4. The LLM synthesizes the final answer.
