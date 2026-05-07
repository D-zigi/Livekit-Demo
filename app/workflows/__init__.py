"""Workflow definitions for LiveKit."""

from typing import Any, Dict

from .meeting_booking import MeetingBookingWorkflow

Workflows = str

workflows: Dict[Workflows, Any] = {
    "meeting_booking": MeetingBookingWorkflow,
}

__all__ = ["workflows"]
