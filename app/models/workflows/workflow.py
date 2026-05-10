"""
Workflow CRUD models
"""
from typing import Literal, Optional
from pydantic import BaseModel, Field

from app.models.workflows.workflow_schema import WorkflowSchema
from app.types import BusinessScopedReadModel

WorkflowVisibility = Literal["public", "private", "template"] # Agent visibility types

class WorkflowCreate(BaseModel):
    """
    WorkflowCreate model used to
    Create a new workflow
    """
    name: str = Field(description="Name")
    description: str = Field(description="Description")
    icon: Optional[str] = Field(default=None, description="Icon")
    flow: WorkflowSchema = Field(description="Workflow Schema")
    visibility: WorkflowVisibility = Field(default="private", description="Visibility")

class WorkflowRead(WorkflowCreate, BusinessScopedReadModel):
    """
    WorkflowRead model used to
    Read a workflow
    """
    business_id: Optional[str] = Field(default=None, description="Business ID")

class WorkflowUpdate(BaseModel):
    """
    WorkflowUpdate model used to
    Update a workflow
    """
    id: str = Field(description="ID")
    name: Optional[str] = Field(default=None, description="Name")
    description: Optional[str] = Field(default=None, description="Description")
    icon: Optional[str] = Field(default=None, description="Icon")
    flow: Optional[WorkflowSchema] = Field(default=None, description="Workflow Schema")
    visibility: Optional[WorkflowVisibility] = Field(default=None, description="Visibility")

class WorkflowDelete(BaseModel):
    """
    WorkflowDelete model used to
    Delete a workflow
    """
    id: str = Field(description="ID")


class Workflow(WorkflowRead):
    """
    Workflow model
    """

class WorkflowBase(WorkflowCreate):
    """
    Workflow base model
    """
