from enum import Enum

# Schedule.status wire values — must stay in sync with mobile
# ScheduleStatus in mobile/lib/utils/constants.dart.
# NOTE: attend.status uses a separate small set ("P"/"AT"/"NG") — do not
# confuse it with Schedule.status.
class Status(str, Enum):
    ACTIVE = "AT"
    PENDING = "PD"
    NOT_GOING = "NG"
    CANCEL = "CL"
    NOT_ATTEND = "NA"
    ATTEND = "AD"
    COMING_SOON = "CS"
    
    
class Type(str, Enum):
    PERSONAL = "PL"
    BUSINESS = "BS"

# 下禮拜跟阿明去故宮

# Mapping for legacy data migration (Optional, logic will be in migration script)
