import uuid
from typing import Optional, Set, Tuple

from fastapi import HTTPException, status

VALID_ROLES: Set[str] = {
    "admin",
    "administrator",
    "manager",
    "employee",
    "peer_reviewer",
    "peer",
}

MANAGER_OR_ADMIN_ROLES: Set[str] = {
    "admin",
    "administrator",
    "manager",
}


def normalize_role(role: Optional[str], default: str = "employee") -> str:
    """
    Safely normalizes and validates a role string.
    Rejects malformed or unrecognized roles, defaulting to least-privilege (employee).
    """
    if not role:
        return default
    cleaned = role.strip().lower()
    if cleaned in VALID_ROLES:
        return cleaned
    return default


def resolve_principal(
    header_id: Optional[uuid.UUID] = None,
    header_role: Optional[str] = None,
    query_id: Optional[uuid.UUID] = None,
    query_role: Optional[str] = None,
    default_role: str = "employee",
) -> Tuple[Optional[uuid.UUID], str]:
    """
    Resolves caller identity and role with strict header precedence.

    Security guarantees:
    - If trusted authenticated headers (X-Viewer-Id / X-Viewer-Role) are present,
      query parameters cannot override them to escalate privileges or spoof actor identity.
    - If a client supplies conflicting query credentials while headers are set,
      the header principal strictly prevails.
    - Roles are validated and normalized to lowercase.
    """
    effective_id: Optional[uuid.UUID] = header_id if header_id is not None else query_id
    effective_raw_role: Optional[str] = header_role if header_role is not None else query_role
    effective_role: str = normalize_role(effective_raw_role, default=default_role)

    return effective_id, effective_role


def verify_manager_or_admin(role: str) -> None:
    """Verifies that the effective role has managerial or administrative privileges."""
    normalized = normalize_role(role)
    if normalized not in MANAGER_OR_ADMIN_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{role}' is not authorized to perform managerial governance actions.",
        )
