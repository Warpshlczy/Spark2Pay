"""
Input Validators
"""
import re


def validate_email(email: str) -> bool:
    """
    Validate email format

    Args:
        email: Email address

    Returns:
        True if valid email format
    """
    if not email:
        return False

    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_password(password: str) -> bool:
    """
    Validate password strength

    Requirements:
    - At least 8 characters
    - At least 1 uppercase letter
    - At least 1 lowercase letter
    - At least 1 number

    Args:
        password: Password to validate

    Returns:
        True if password meets requirements
    """
    if not password or len(password) < 8:
        return False

    has_upper = bool(re.search(r'[A-Z]', password))
    has_lower = bool(re.search(r'[a-z]', password))
    has_digit = bool(re.search(r'\d', password))

    return has_upper and has_lower and has_digit


def validate_username(username: str) -> bool:
    """
    Validate username

    Requirements:
    - 3-50 characters
    - Alphanumeric, underscore, dash only
    - Must start with letter or number

    Args:
        username: Username to validate

    Returns:
        True if valid username
    """
    if not username or len(username) < 3 or len(username) > 50:
        return False

    pattern = r'^[a-zA-Z0-9][a-zA-Z0-9_-]*$'
    return bool(re.match(pattern, username))
