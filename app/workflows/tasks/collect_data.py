"""
Data collection tasks for the copilot session.
"""
import logging
from dataclasses import dataclass
from typing import Any

from livekit.agents import AgentTask, function_tool
from livekit.agents.beta.workflows import (
    GetEmailTask as _GetEmailTask,
    GetEmailResult,
    GetAddressTask as _GetAddressTask,
    GetAddressResult,
    GetDtmfTask as _GetDtmfTask,
    GetDtmfResult,
)

from app.utils.data_validation import validate_email_address

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# LiveKit built-in task wrappers — add copilot hooks via multiple inheritance.
# MRO: CopilotWrapper -> AgentTask -> _LiveKitTask -> AgentTask
# AgentTask.__init__ consumes `copilot_agent` and forwards **kwargs down.
# ---------------------------------------------------------------------------

class GetEmailTask(_GetEmailTask):
    """GetEmailTask with copilot context injection and text suppression."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)


class GetAddressTask(_GetAddressTask):
    """GetAddressTask with copilot context injection and text suppression."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)


class GetDtmfTask(_GetDtmfTask):
    """GetDtmfTask with copilot context injection and text suppression."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)


# ---------------------------------------------------------------------------
# Custom tasks
# ---------------------------------------------------------------------------

@dataclass
class EmailResult:
    email: str


class CollectEmailTask(AgentTask[EmailResult]):
    """Collects and validates an email address from the user."""

    def __init__(self, extra_instructions: str = "", **kwargs: Any) -> None:
        super().__init__(
            instructions="Collect email information from the user for the specified purpose.\n"
                         + extra_instructions,
            **kwargs,
        )

    async def on_enter(self) -> None:
        await self.session.generate_reply(
            instructions="Politely ask the user for their email address for the specified purpose."
        )

    @function_tool
    async def email_given(self, email: str) -> None:
        """Use this when the user provides an email address."""
        validation = await validate_email_address(email)
        if not validation[0]:
            await self.session.generate_reply(
                instructions=f"The email '{email}' is invalid: {validation[1]}. Ask for a valid email."
            )
            return
        self.complete(EmailResult(email=validation[1]))


@dataclass
class CompanyResult:
    name: str
    nature: str


class CollectCompanyTask(AgentTask[CompanyResult]):
    """Collects company name and nature from the user."""

    def __init__(self, extra_instructions: str = "", **kwargs: Any) -> None:
        super().__init__(
            
            instructions="Collect company information from the user for the specified purpose.\n"
                         + extra_instructions,
            **kwargs,
        )

    async def on_enter(self) -> None:
        await self.session.generate_reply(
            instructions="Politely ask the user for their company name and what the company does."
        )

    @function_tool
    async def company_info_given(self, name: str, nature: str) -> None:
        """Use when the user provides company name and nature.

        Args:
            name: The name of the company.
            nature: The nature / industry of the company.
        """
        self.complete(CompanyResult(name=name, nature=nature))


__all__ = [
    "GetEmailTask",
    "GetEmailResult",
    "GetAddressTask",
    "GetAddressResult",
    "GetDtmfTask",
    "GetDtmfResult",
    "EmailResult",
    "CollectEmailTask",
    "CompanyResult",
    "CollectCompanyTask",
]
