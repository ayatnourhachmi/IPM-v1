"""Deterministic filtering of LLM role picks against an explicit allow-list."""

from __future__ import annotations

import logging
from collections import defaultdict

from app.schemas.business_need import ExpertiseTeamRoleSlot

logger = logging.getLogger(__name__)


def _norm_key(role: str) -> str:
    return " ".join(role.strip().lower().split())


def dedupe_allowed_roles(roles: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for r in roles:
        s = r.strip()
        if not s:
            continue
        k = _norm_key(s)
        if k in seen:
            continue
        seen.add(k)
        out.append(s)
    return out


def _build_role_lookup(allowed_roles: list[str]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for canonical in allowed_roles:
        lookup[_norm_key(canonical)] = canonical
    return lookup


def constrain_team_to_allowed_roles(
    raw_team: object,
    allowed_roles: list[str],
) -> list[ExpertiseTeamRoleSlot]:
    """Keep only roles present in *allowed_roles* (case/spacing insensitive); merge counts."""
    lookup = _build_role_lookup(allowed_roles)
    counts: dict[str, int] = defaultdict(int)

    if not isinstance(raw_team, list):
        return []

    for item in raw_team:
        if not isinstance(item, dict):
            continue
        role_raw = item.get("role")
        if role_raw is None:
            continue
        role_str = str(role_raw).strip()
        if not role_str:
            continue
        matched = lookup.get(_norm_key(role_str))
        if matched is None:
            logger.info("Expertise team constraint: dropped unknown role %r", role_str)
            continue
        try:
            c = int(item.get("count", 1))
        except (TypeError, ValueError):
            c = 1
        if c < 1:
            continue
        c = min(c, 99)
        counts[matched] += c

    return [ExpertiseTeamRoleSlot(role=r, count=n) for r, n in sorted(counts.items())]
