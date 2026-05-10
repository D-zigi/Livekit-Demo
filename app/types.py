"""
Defines types and constants used across the application.
"""
from typing import Literal, Optional
from pydantic import BaseModel, Field

# Status types used for various entities
Status = Literal["pending", "in_progress", "completed", "failed", "canceled"]

# Call types used for call-related entities
CallDirection = Literal["inbound", "outbound"]

# Deal types used for deal-related entities
DealStatus = Literal["lead", "contacted", "qualified", "proposals_made", "won", "lost"]

# Base read model
class BaseReadModel(BaseModel):
    """
    Base read model
    """
    id: str = Field(description="ID")
    created_at: str = Field(description="Created at")
    updated_at: Optional[str] = Field(default=None, description="Updated at")

# Business scoped read model
class BusinessScopedReadModel(BaseReadModel):
    """
    Business scoped read model
    """
    business_id: str = Field(description="Business ID")

__all__ = [
    "Status",
    "CallDirection",
    "DealStatus",
    "BaseReadModel",
    "BusinessScopedReadModel"
]
