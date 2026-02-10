from enum import Enum

class Status(str, Enum):
    ACTIVE = "A"
    PENDING = "P"
    NOT_GOING = "N"
    CANCEL = "C"

# Mapping for legacy data migration (Optional, logic will be in migration script)
