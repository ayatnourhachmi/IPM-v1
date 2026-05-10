"""LLM-assisted team sizing constrained to an explicit role allow-list."""

from __future__ import annotations

from typing import Any

from app.core.expertise_roles import DEFAULT_ALLOWED_EXPERTISE_ROLES
from app.core import llm_client
from app.services.expertise_team_constraints import (
    constrain_team_to_allowed_roles,
    dedupe_allowed_roles,
)
from app.schemas.business_need import ExpertiseTeamEstimateResponse

__all__ = ["estimate_expertise_team"]


async def estimate_expertise_team(
    solution_description: str,
    allowed_roles: list[str] | None = None,
) -> ExpertiseTeamEstimateResponse:
    """Call LLM then enforce allow-list (no invented roles in the response)."""
    roles = dedupe_allowed_roles(list(allowed_roles or []))
    if not roles:
        roles = list(DEFAULT_ALLOWED_EXPERTISE_ROLES)

    bullet_list = "\n".join(f"- {r}" for r in roles)
    rsp = await llm_client.complete(
        prompt_name="expertise-team-estimation",
        variables={
            "solution_description": solution_description.strip(),
            "allowed_roles_list": bullet_list,
            "explicit": (
                "Estimate a minimal credible delivery team for the solution described, "
                "using ONLY the supplied role labels."
            ),
            "implicit": "Prefer fewer roles with realistic headcount; omit roles that add no clear value.",
            "strategic": "Reflect enterprise delivery patterns (governance, build, operate) without inventing new job titles.",
        },
        response_format="json",
    )
    parsed: dict[str, Any] = llm_client.parse_json_response(rsp)
    team = constrain_team_to_allowed_roles(parsed.get("team"), roles)
    return ExpertiseTeamEstimateResponse(team=team)
