"""
Workflow Node Data Models
"""
from typing import Annotated, Any, Literal, Optional, Union, List
from pydantic import BaseModel, Discriminator, Field, model_validator

TaskResultFieldType = Literal['string', 'number', 'boolean', 'enum']
TaskResultType = Literal[TaskResultFieldType, 'object']

# Start Node
class StartNodeData(BaseModel):
    type: Literal["start"] = "start"
    label: Literal["start"] = "start"

# Task Node
class TaskCompletionTool(BaseModel):
    id: str = Field(description="ID")
    name: str = Field(description="Name")
    description: str = Field(description="Description")
    # Used to generate function without the value parameter, and use the predefined value to complete the task.
    value: Optional[Any] = Field(default=None, description="Value")


class TaskResultFieldBase(BaseModel):
    id: str = Field(description="ID")
    name: str = Field(description="Name")
    description: str = Field(description="Description")
    required: bool = Field(description="Required")

class TaskResultFieldEnum(TaskResultFieldBase):
    type: Literal["enum"] = "enum"
    enum_values: List[str] = Field(min_length=1, description="Enum Values")

class TaskResultFieldGeneric(TaskResultFieldBase):
    type: Literal["string", "number", "boolean"] = Field(description="Field Type")

TaskResultField = Annotated[
    Union[
        TaskResultFieldEnum,
        TaskResultFieldGeneric,
    ],
    Discriminator("type")
]

class TaskNodeDataBase(BaseModel):
    type: Literal["task"] = "task"
    label: str = Field(description="Label")
    instructions: str = Field(description="Instructions")
    completion_tools: List[TaskCompletionTool] = Field(min_length=1, description="Completion Tools")

class TaskNodeDataObject(TaskNodeDataBase):
    result_type: Literal["object"] = Field(description="Result Type")
    result_fields: List[TaskResultField] = Field(default_factory=list, description="Result Fields")

class TaskNodeDataEnum(TaskNodeDataBase):
    result_type: Literal["enum"] = Field(description="Result Type")
    enum_values: List[str] = Field(min_length=1, description="Enum Values")

    @model_validator(mode="after")
    def _check_enum_values(self) -> "TaskNodeDataEnum":
        n = len(self.completion_tools)
        if n < len(self.enum_values):
            raise ValueError("Enum tasks need at least as many completion tools as enum values")
        return self

class TaskNodeDataBoolean(TaskNodeDataBase):
    result_type: Literal["boolean"] = Field(description="Result Type")
    completion_tools: List[TaskCompletionTool] = Field(min_length=2, description="Completion Tools")

class TaskNodeDataGeneric(TaskNodeDataBase):
    result_type: Literal["string", "number"] = Field(description="Result Type")

TaskNodeData = Annotated[
    Union[
        TaskNodeDataObject,
        TaskNodeDataEnum,
        TaskNodeDataBoolean,
        TaskNodeDataGeneric,
    ],
    Discriminator("result_type")
]

# Say Node
class SayNodeData(BaseModel):
    type: Literal["say"] = "say"
    label: str = Field(description="Label")
    instructions: str = Field(description="Instructions")
    allow_interruptions: bool = Field(description="Allow Interruptions")

# End Node
class EndNodeData(BaseModel):
    type: Literal["end"] = "end"
    label: Literal["end"] = "end"
    closing_message: Optional[str] = Field(default=None, description="Closing Message")


__all__ = [
    "StartNodeData",
    "TaskNodeData",
    "SayNodeData",
    "EndNodeData",
]