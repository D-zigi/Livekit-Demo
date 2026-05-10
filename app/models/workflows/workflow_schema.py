"""
Workflow CRUD models
"""
from typing import Annotated, Any, Literal, Optional, Union, List

from pydantic import BaseModel, Discriminator, Field, model_validator
from .nodes_schemas import (
    StartNodeData,
    TaskNodeData,
    SayNodeData,
    EndNodeData,
)


# Workflow Node
WorkflowDataType =  Annotated[
    Union[
        StartNodeData,
        TaskNodeData,
        SayNodeData,
        EndNodeData,
    ],
    Discriminator("type")
]

class WorkflowNode(BaseModel):
    id: str = Field(description="ID")
    type: str = Field(description="Type")
    position: dict = Field(description="Position")
    data: WorkflowDataType = Field(description="Data")

    @model_validator(mode="after")
    def infer_type(self):
        self.type = self.data.type
        return self

# Workflow Edge
WorkflowEdgeKind = Literal[
    'session-start',
    'task-run',
    'task-result',
]

class WorkflowEdge(BaseModel):
    id: str = Field(description="ID")
    source: str = Field(description="Source")
    target: str = Field(description="Target")
    label: str = Field(description="Label")
    kind: WorkflowEdgeKind = Field(description="Kind")
    task_result_key: Optional[Any] = Field(default=None, description="Task Result Key")

class WorkflowSchema(BaseModel):
    """
    WorkflowSchema model
    """
    entry_node_id: str = Field(description="Entry Node ID")
    nodes: List[WorkflowNode] = Field(default_factory=list, description="Nodes")
    edges: List[WorkflowEdge] = Field(default_factory=list, description="Edges")
