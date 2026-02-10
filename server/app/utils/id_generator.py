import uuid

def generate_id(prefix: str) -> str:
    """
    Generates a custom ID with the format: {prefix}{uuid_hex}
    Example: ur550e8400e29b41d4a716446655440000
    """
    return f"{prefix}{uuid.uuid4().hex}"

def generate_user_id() -> str:
    return generate_id("ur")

def generate_schedule_id() -> str:
    return generate_id("se")

def generate_contact_id() -> str:
    return generate_id("ct")

def generate_attendee_id() -> str:
    return generate_id("atd")
