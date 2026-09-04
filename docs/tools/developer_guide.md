# Developer Guide: Adding a New Tool

Follow these steps to add a new tool adapter to the Phase 8 Tool Calling Framework.

## 1. Create the Adapter Class

Create a new file in `src/infrastructure/tools/adapters/`. Your class must implement `ITool`.

```python
from typing import Any, Dict
from src.domain.interfaces.tools import ITool
from src.domain.models.tools import PermissionLevel, ToolMetadata, ToolResult

class MyCustomTool(ITool):
    def get_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="my_custom_tool",
            description="Does something awesome.",
            permissions=PermissionLevel.READ_ONLY, # READ_ONLY, RESTRICTED, or ADMIN_ONLY
            input_schema={
                "type": "object",
                "properties": {
                    "my_arg": {"type": "string"}
                },
                "required": ["my_arg"]
            },
            output_schema={"type": "object"},
            timeout_seconds=10.0,
            retry_policy={"max_retries": 2, "backoff_factor": 1.5}
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        my_arg = kwargs.get("my_arg")
        try:
            # Your logic here
            return ToolResult(success=True, data={"echo": my_arg})
        except Exception as e:
            return ToolResult(success=False, error=str(e))
```

## 2. Register the Tool

Open `src/interfaces/api/dependencies.py` and locate `get_tool_manager()`.
Register your new tool adapter with the `ToolRegistry`:

```python
from src.infrastructure.tools.adapters.my_custom_tool import MyCustomTool

def get_tool_manager(memory_svc=None):
    registry = ToolRegistry()
    
    # ... existing registrations ...
    registry.register(MyCustomTool())
    
    return ToolManager(registry, metrics)
```

## 3. Security Considerations

- **No Code Execution**: Do not implement features that allow `eval()`, shell execution, or remote code execution.
- **Path Traversal**: If your tool reads local files, enforce boundaries strictly (see `LocalFileSystemAdapter`).
- **Permissions**: Assign `RESTRICTED` or `ADMIN_ONLY` if the tool accesses sensitive configuration, memory scopes, or writes data (when write capabilities are enabled in the future).
