"""
Utility functions for conversation handling.
"""

def is_thought(message: str) -> bool:
    """
    Check if the message is a thought.

    Args:
        message (str): The message to check.
    Returns:
        bool: True if the message is a thought, False otherwise.
    """
    words = message.split(" ")
    if len(words) >= 10:
        return True
    return False
