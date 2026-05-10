"""Synthesize an AgentTask subclass from TaskNodeData."""
from typing import Any, Literal

from livekit.agents import AgentTask, function_tool
from livekit.agents.llm import Tool, Toolset
from pydantic import BaseModel, TypeAdapter, create_model

from app.models.workflows.nodes_schemas import (
    TaskCompletionTool,
    TaskNodeData,
    TaskNodeDataBoolean,
    TaskNodeDataObject,
    TaskResultFieldType,
)


def python_type_for(
    result_type: TaskResultFieldType,
    enum_values: list[str] | None = None,
) -> Any:
    """Map a TaskResultFieldType literal to a Python type."""
    match result_type:
        case "string":
            return str
        case "number":
            return float
        case "boolean":
            return bool
        case "enum":
            if not enum_values:
                raise ValueError("enum_values required for enum type")
            return Literal[tuple(enum_values)]
        case _:
            raise ValueError(f"unsupported result type: {result_type}")

def _object_result_model(data: TaskNodeDataObject) -> type[BaseModel]:
    """Build a pydantic model from result_fields. The model both types T for
    AgentTask[T] and validates completion values at runtime."""
    fields: dict[str, Any] = {}
    for f in data.result_fields:
        ft = python_type_for(f.type, getattr(f, "enum_values", None))
        fields[f.name] = (ft, ...) if f.required else (ft | None, None)
    return create_model(f"{data.label}Result", **fields)

def _result_type_for(data: TaskNodeData) -> Any:
    """T for AgentTask[T] and the type of the value parameter on completion tools."""
    if isinstance(data, TaskNodeDataObject):
        return _object_result_model(data)
    return python_type_for(data.result_type, getattr(data, "enum_values", None))


def _make_completion_tool(
    task: AgentTask,
    tool_def: TaskCompletionTool,
    data: TaskNodeData,
    T: Any,
):
    if tool_def.value is not None:
        return _make_preset_tool(task, tool_def, T)

    if isinstance(data, TaskNodeDataBoolean):
        raise ValueError(
            f"boolean completion tool {tool_def.name!r} must have a preset value"
        )

    return _make_value_tool(task, tool_def, T)

def _make_preset_tool(
    task: AgentTask,
    tool_def: TaskCompletionTool,
    T: Any,
):
    validated = TypeAdapter(T).validate_python(tool_def.value)

    @function_tool(name=tool_def.name, description=tool_def.description)
    async def preset_tool() -> None:
        task.complete(validated)

    return preset_tool

def _make_value_tool(task: AgentTask, tool_def: TaskCompletionTool, value_type: Any):
    """Single-param completion tool. Annotation is patched in because the param
    type is computed at runtime and pyright won't allow a variable in an annotation."""
    async def value_tool(value):
        task.complete(value)

    value_tool.__annotations__ = {"value": value_type, "return": type(None)}
    return function_tool(name=tool_def.name, description=tool_def.description)(value_tool)


def build_task(data: TaskNodeData) -> type[AgentTask]:
    T = _result_type_for(data)

    class _SynthesizedTask(AgentTask[T]):
        def __init__(self, **_):
            super().__init__(instructions=data.instructions)
            self._completion_tools: list[Tool | Toolset] = [
                _make_completion_tool(self, t, data, T) for t in data.completion_tools
            ]

        async def on_enter(self) -> None:
            await self.update_tools(self._completion_tools)

    _SynthesizedTask.__name__ = f"{data.label}Task"
    return _SynthesizedTask


__all__ = ["build_task"]
