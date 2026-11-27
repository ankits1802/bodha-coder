from app.models import PRACTICE_MEMBER_ROLES

PRACTICE_ROLES = PRACTICE_MEMBER_ROLES
HQ_ROLE = "hq"
HQ = (HQ_ROLE,)
ADMIN_ROLE = "admin"
ADMINS = (ADMIN_ROLE,)
PLAN_MANAGERS = ADMINS
UPLOADERS = ("admin", "coder")
NOTE_READERS = ("admin", "coder", "cdi", "compliance", "biller")
DECIDERS = ("admin", "coder", "cdi", "compliance")
APPROVERS = ("admin", "coder", "compliance")
ASKERS = ("admin", "coder", "cdi")
ASSIGNERS = ("admin", "coder", "cdi")
COMPLIANCE = ("admin", "compliance")
BILLERS = ("admin", "biller")
INSIGHT_READERS = ("admin", "compliance", "viewer")
INVITABLE_ROLES = PRACTICE_ROLES
