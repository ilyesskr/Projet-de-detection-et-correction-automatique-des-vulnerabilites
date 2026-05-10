"""Re-export every ORM model so a single ``from app import models`` import is
enough for Alembic autogeneration to see the full schema, and so consumers can
write ``from app.models import Asset`` without knowing the file layout.
"""

from app.models.asset import Asset
from app.models.audit import AuditLog
from app.models.remediation import RemediationJob
from app.models.role import Role, user_role_table
from app.models.user import User, user_asset_scope_table
from app.models.vulnerability import Vulnerability

__all__ = [
    "Asset",
    "AuditLog",
    "RemediationJob",
    "Role",
    "User",
    "Vulnerability",
    "user_asset_scope_table",
    "user_role_table",
]
