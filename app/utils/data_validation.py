import asyncio
from email_validator import validate_email, EmailNotValidError

async def validate_email_address(email: str) -> tuple[bool, str]:
    """
    Full email online validation with DNS and deliverability checks.

    Args:
        email (str): The email address to validate.

    Returns:
        tuple[bool, str]: A tuple containing a boolean indicating whether the email is valid and a string with the normalized email address.
    """
    try:
        # This checks DNS MX records
        validated = await asyncio.to_thread(validate_email, email, check_deliverability=True)
        return (True, validated.normalized)
    except EmailNotValidError as e:
        return (False, str(e))
