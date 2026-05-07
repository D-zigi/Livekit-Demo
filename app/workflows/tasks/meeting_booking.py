"""
Meeting booking tasks for the voice agent.
"""
import logging
from dataclasses import dataclass
from typing import Optional

from livekit.agents import AgentTask, ToolError, function_tool

logger = logging.getLogger(__name__)


@dataclass
class MeetingDetails:
    event_id: str
    date: str
    time: str
    formatted_datetime: str


@dataclass
class ExistingMeetingDecision:
    wants_reschedule: bool


@dataclass
class PreferredTimeResult:
    date: str  # YYYY-MM-DD
    time: str  # HH:MM (24-hour)


@dataclass
class MeetingBookingResponse:
    message: dict
    email: dict
    event: dict


class CheckExistingMeetingTask(AgentTask[Optional[ExistingMeetingDecision]]):
    """
    Check if the client has an existing meeting.
    Ask user if they want to reschedule their existing meeting or keep it.
    """

    def __init__(self, extra_instructions: str = "", *args, **kwargs):
        super().__init__(
            instructions="""
            Check if the client has an existing meeting.
            If they have one, ask if they want to keep it or reschedule to a different time.
            Make it clear they can only have one meeting at a time.
            Proceed with the booking if none exists.
            If an existing meeting is found, ask if they want to keep it or reschedule.
            If they choose to keep it, complete the workflow,
            send a reminder in gmail and message(whatsapp/sms) and end the call.
            If they choose to reschedule, proceed with the booking.
            """ + extra_instructions,
            *args, **kwargs
        )

    async def on_enter(self) -> None:
        await self.session.generate_reply(
            instructions="Inform the client about checking their existing meeting."
        )

    @function_tool
    async def handle_proceed(self) -> None:
        """Handle proceeding with the booking."""
        await self.session.generate_reply(instructions="Proceed with the booking.")
        self.complete(None)

    @function_tool
    async def wants_to_reschedule(self) -> None:
        """Use when client wants to change to a different date/time."""
        self.complete(ExistingMeetingDecision(wants_reschedule=True))

    @function_tool
    async def keeps_existing_meeting(self) -> None:
        """Use when client wants to keep their current meeting."""
        self.complete(ExistingMeetingDecision(wants_reschedule=False))


class CollectPreferredTimeTask(AgentTask[PreferredTimeResult]):
    """
    Collect client's preferred meeting date and time.

    This only collects the preference - availability check happens at Agent level.
    """

    def __init__(self, extra_instructions: str = "", *args, **kwargs):
        super().__init__(
            instructions="""
            Collect the client's preferred date and time for the meeting.
            Meetings are available Monday-Friday, 9 AM to 5 PM Central Time.
            """ + extra_instructions,
            *args, **kwargs
        )

    async def on_enter(self) -> None:
        await self.session.generate_reply(
            instructions="Ask the client when they would like to schedule their meeting. "
                         "Mention availability: Monday-Friday, 9 AM - 5 PM Central Time."
        )

    @function_tool
    async def time_provided(self, date: str, time: str) -> None:
        """
        Use when client provides their preferred date and time.

        Args:
            date: Preferred date in YYYY-MM-DD format (e.g., 2025-01-15)
            time: Preferred time in HH:MM 24-hour format (e.g., 14:30)
        """
        self.complete(PreferredTimeResult(date=date, time=time))


class MeetingBookingTask(AgentTask[MeetingBookingResponse]):
    """
    MeetingBookingTask - Book meeting, send confirmations, and verify with client.

    Flow:
    1. Book the meeting using the calendar tool with previously discussed details
    2. Send confirmation email via Gmail
    3. Send confirmation message via WhatsApp or SMS
    4. Verify with the client that they received everything
    5. Iterate if they haven't received confirmations
    """

    def __init__(self, extra_instructions: str = "", *args, **kwargs):
        super().__init__(
            instructions="""
            Your task is to complete the meeting booking process:

            1. BOOK THE MEETING: Use the calendar tool to create the meeting with the
               date, time, and details discussed earlier in the conversation.

            2. SEND CONFIRMATIONS: After booking successfully:
               - Send a confirmation email using the Gmail tool
               - Send a confirmation message using WhatsApp or SMS (prefer WhatsApp if available)

            3. VERIFY WITH CLIENT: Ask the client to confirm they received:
               - The calendar invite
               - The confirmation email
               - The WhatsApp/SMS message

            4. ITERATE IF NEEDED: If the client hasn't received any confirmation:
               - Ask them to check spam/junk folders
               - Verify their contact details are correct
               - Resend if necessary using the appropriate tool

            You have access to the tools for calendar, email, and messaging - use them
            to complete each step before moving to verification.
            """ + extra_instructions,
            *args, **kwargs
        )
        self.message = None
        self.email = None
        self.event = None
        self.confirmed = False

    async def on_enter(self) -> None:
        await self.session.generate_reply(
            instructions="""
            Let the client know you're now going to:
            1. Book their meeting with the details you discussed
            2. Send them a confirmation email
            3. Send them a WhatsApp/SMS confirmation

            Then proceed to use the calendar tool to book the meeting with the
            previously discussed date, time, and details. After that, send the
            confirmation email and message.
            """
        )

    @function_tool
    async def booking_and_confirmations_sent(self) -> None:
        """
        Use after you have successfully:
        1. Created the calendar event
        2. Sent the confirmation email
        3. Sent the WhatsApp/SMS message

        This triggers verification with the client.
        """
        if self.event and self.email and self.message and self.confirmed:
            await self.session.generate_reply(
                instructions="""
                Confirm to the client that you've booked their meeting and sent confirmations.
                Ask them to check and confirm they received the calendar invite, email, and message.
                """
            )
            self.complete(MeetingBookingResponse(
                message=self.message,
                email=self.email,
                event=self.event,
            ))
        else:
            raise ToolError("Booking and confirmations not sent")

    @function_tool
    async def event_created(self, event: dict) -> None:
        """Use when calendar event is created."""
        self.event = event

    @function_tool
    async def email_sent(self, email: str, content: str) -> None:
        """Use when email confirmation is sent."""
        self.email = {"email": email, "content": content}

    @function_tool
    async def message_sent(self, phone_number: str, content: str) -> None:
        """Use when WhatsApp/SMS message is sent."""
        self.message = {"phone_number": phone_number, "content": content}

    @function_tool
    async def user_confirms(self) -> None:
        """Use when client confirms they received all confirmations."""
        self.confirmed = True

    @function_tool
    async def user_declines(self) -> None:
        """Use when client says they don't see any confirmation."""
        await self.session.generate_reply(
            instructions="Ask the client to verify their email address and phone number. "
                         "If any were wrong, get the correct ones and resend."
        )
        self.confirmed = False
