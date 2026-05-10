"""Permission catalog and role-to-permission mapping.

The set of permissions is fixed and code-defined, so we keep them in a
``StrEnum`` rather than a ``permissions`` table. ``ROLE_PERMISSIONS`` maps
each named role to the permissions it grants. Routes ask for permissions by
name; ``get_current_user`` resolves the user's roles to a permission set on
every request, so a role change takes effect on the user's next API call —
not when their JWT expires.
"""

from __future__ import annotations

from enum import StrEnum


class Permission(StrEnum):
    """Catalog of every permission the platform recognizes.

    Names use ``resource:action`` so they read naturally in route decorators
    and in audit logs. ``remediation:read`` is intentionally distinct from the
    write permissions so that any of {create, approve, launch} grants list /
    detail access without OR-ing three permissions on every read route.
    """

    ASSETS_READ            = "assets:read"
    VULNERABILITIES_READ   = "vulnerabilities:read"
    INTEGRATIONS_READ      = "integrations:read"
    AUDIT_READ             = "audit:read"
    SYNC_RUN               = "sync:run"
    REMEDIATION_READ       = "remediation:read"
    REMEDIATION_CREATE     = "remediation:create"
    REMEDIATION_APPROVE    = "remediation:approve"
    REMEDIATION_LAUNCH     = "remediation:launch"
    REMEDIATION_VERIFY     = "remediation:verify"
    USERS_MANAGE           = "users:manage"


class Role(StrEnum):
    """The four named roles seeded by ``scripts/create_admin.py``.

    Other roles can exist in the database, but these four are guaranteed to
    be present and are referenced by the bootstrap and tests by name.
    """

    ADMIN                = "admin"
    SECURITY_ANALYST     = "security_analyst"
    REMEDIATION_OPERATOR = "remediation_operator"
    VIEWER               = "viewer"


# Role → permissions. ``admin`` gets everything by construction so the set
# below stays in sync if we add a new permission. The other three roles are
# explicit — adding a permission must be a deliberate choice per role.
ROLE_PERMISSIONS: dict[str, frozenset[Permission]] = {
    Role.VIEWER.value: frozenset({
        Permission.ASSETS_READ,
        Permission.VULNERABILITIES_READ,
        Permission.INTEGRATIONS_READ,
        Permission.AUDIT_READ,
    }),
    Role.SECURITY_ANALYST.value: frozenset({
        Permission.ASSETS_READ,
        Permission.VULNERABILITIES_READ,
        Permission.INTEGRATIONS_READ,
        Permission.AUDIT_READ,
        Permission.SYNC_RUN,
        Permission.REMEDIATION_READ,
        Permission.REMEDIATION_CREATE,
    }),
    Role.REMEDIATION_OPERATOR.value: frozenset({
        Permission.ASSETS_READ,
        Permission.VULNERABILITIES_READ,
        Permission.INTEGRATIONS_READ,
        Permission.AUDIT_READ,
        Permission.SYNC_RUN,
        Permission.REMEDIATION_READ,
        Permission.REMEDIATION_APPROVE,
        Permission.REMEDIATION_LAUNCH,
        Permission.REMEDIATION_VERIFY,
    }),
    Role.ADMIN.value: frozenset(Permission),
}


def permissions_for_roles(role_names: list[str] | set[str]) -> frozenset[Permission]:
    """Union the permissions granted by every role in ``role_names``.

    Unknown role names are ignored — a stale role left over from a previous
    deploy should not crash the request, it should just contribute nothing.
    """
    result: set[Permission] = set()
    for name in role_names:
        result |= ROLE_PERMISSIONS.get(name, frozenset())
    return frozenset(result)
