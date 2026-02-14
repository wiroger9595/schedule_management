from enum import Enum

class Status(str, Enum):
    ACTIVE = "AT"
    PENDING = "PD"
    NOT_GOING = "NG"
    CANCEL = "CL"
    NOT_ATTEND = "NA"
    ATTEND = "AT"
    COMING_SOON = "CS"
    
    
class Type(str, Enum):
    PERSONAL = "PL"
    BUSINESS = "BS"



# Mapping for legacy data migration (Optional, logic will be in migration script)
