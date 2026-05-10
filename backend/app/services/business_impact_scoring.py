"""Hybrid business impact: deterministic alignment (1–4) + LLM phrasing grounded in catalog rows only."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.core import llm_client
from app.schemas.business_need import BusinessImpactScoreResponse, CatalogImpactReference
from app.services.catalog_loader import Solution, catalog_loader

logger = logging.getLogger(__name__)

_EXCEL_ID = re.compile(r"^EXCEL-(\d+)$", re.IGNORECASE)


def _domains_match(solution_domain: str, need_domains: list[str]) -> bool:
    if not solution_domain:
        return True
    sol = solution_domain.strip().lower()
    if sol == "autre":
        return True
    for nd in need_domains:
        nd_l = nd.strip().lower()
        if nd_l == "autre":
            return True
        if sol in nd_l or nd_l in sol:
            return True
    return False


_OBJECTIVE_HINTS: dict[str, tuple[str, ...]] = {
    "cost_reduction": ("cost", "efficien", "réduction", "reduction", "automat", "save", "productiv"),
    "cx_improvement": ("customer", "experience", "satisfaction", "service", "user", "client"),
    "risk_mitigation": ("risk", "compliance", "security", "réglement", "regulatory", "resilience"),
    "market_opportunity": ("market", "revenue", "growth", "commercial", "new product", "competitive"),
}

_IMPACT_HINTS: dict[str, tuple[str, ...]] = {
    "revenue": ("revenue", "growth", "sales", "commercial", "top-line", "upsell"),
    "cost": ("cost", "efficien", "automat", "opex", "saving", "productiv"),
    "risk": ("risk", "compliance", "security", "fraud", "breach", "resilience"),
    "customerexperience": ("customer", "experience", "nps", "satisfaction", "cx", "service quality"),
}


def _norm_token(s: str) -> str:
    return "".join(c for c in s.strip().lower() if c.isalnum())


def _solution_text_blob(sol: Solution) -> str:
    parts = [
        sol.description or "",
        sol.target_objective or "",
        " ".join(sol.features[:12]),
        " ".join(sol.limitations[:5]),
        sol.ipm_stage or "",
    ]
    return " ".join(parts).lower()


def _impact_objective_coherent(need_objective: str, need_impact: str, solution: Solution) -> bool:
    blob = _solution_text_blob(solution)
    if len(blob.strip()) < 8:
        return False

    obj_l = need_objective.strip().lower()
    if obj_l in _OBJECTIVE_HINTS:
        return any(h in blob for h in _OBJECTIVE_HINTS[obj_l])

    obj_key = obj_l.replace("_", "")
    for key, hints in _OBJECTIVE_HINTS.items():
        if key == obj_l or key.replace("_", "") == obj_key:
            return any(h in blob for h in hints)

    imp_raw = need_impact.strip()
    if not imp_raw:
        return False
    imp_key = _norm_token(imp_raw)
    for ik, hints in _IMPACT_HINTS.items():
        if _norm_token(ik) == imp_key or ik.lower() == imp_raw.lower():
            return any(h in blob for h in hints)
    return False


def solution_from_catalog_id(catalog_id: str) -> tuple[str, Solution] | None:
    m = _EXCEL_ID.match(catalog_id.strip())
    if not m:
        logger.warning("Invalid catalog id for impact scoring: %r", catalog_id)
        return None
    idx = int(m.group(1)) - 1
    solutions = catalog_loader.get_solutions()
    if idx < 0 or idx >= len(solutions):
        return None
    pid = f"EXCEL-{idx + 1}"
    return pid, solutions[idx]


def catalog_case_dict(pid: str, sol: Solution) -> dict[str, Any]:
    return {
        "catalog_id": pid,
        "solution_name": sol.solution_name,
        "description": sol.description,
        "domain": sol.domain,
        "target_objective": sol.target_objective,
        "maturity": sol.maturity,
        "deployments": sol.deployments,
        "client_sectors": sol.client_sectors,
        "features": sol.features[:25],
        "limitations": sol.limitations[:15],
        "complexity": sol.complexity,
        "ipm_stage": sol.ipm_stage,
    }


def _related_catalog_cases(
    primary_pid: str,
    primary: Solution,
    need_domains: list[str],
    *,
    limit: int = 2,
) -> list[tuple[str, Solution]]:
    out: list[tuple[str, Solution]] = []
    anchor = [primary.domain] if (primary.domain or "").strip() else list(need_domains)
    if not anchor:
        return []
    all_sols = catalog_loader.get_solutions()
    for idx, sol in enumerate(all_sols):
        pid = f"EXCEL-{idx + 1}"
        if pid == primary_pid:
            continue
        if not _domains_match(sol.domain or "", anchor):
            continue
        out.append((pid, sol))
    out.sort(key=lambda t: (t[1].solution_name or "").lower())
    return out[:limit]


def compute_alignment_score_1_4(
    *,
    need_domains: list[str],
    need_objective: str,
    need_impact: str,
    primary: Solution,
) -> int:
    """Deterministic alignment of the business need signals to the catalog solution (1 weak → 4 strong)."""
    score = 1
    if _domains_match(primary.domain or "", need_domains):
        score += 1
    if _impact_objective_coherent(need_objective, need_impact, primary):
        score += 1
    if primary.deployments >= 3:
        score += 1
    return max(1, min(4, score))


def _sanitize_references(
    raw: object,
    allowed: dict[str, dict[str, Any]],
) -> list[CatalogImpactReference]:
    if not isinstance(raw, list):
        return []
    out: list[CatalogImpactReference] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        cid = str(item.get("catalog_id", "")).strip()
        if cid not in allowed or cid in seen:
            continue
        seen.add(cid)
        stmt = str(item.get("statement", "")).strip()
        if not stmt:
            continue
        canon = allowed[cid]
        out.append(
            CatalogImpactReference(
                catalog_id=cid,
                solution_name=str(canon["solution_name"]),
                statement=stmt[:1200],
            )
        )
    return out


async def score_business_impact(
    *,
    pitch: str,
    domains: list[str],
    objective: str,
    impact: str,
    catalog_id: str,
) -> BusinessImpactScoreResponse:
    """Rules-first alignment, then LLM summaries that may only echo supplied catalog JSON."""
    resolved = solution_from_catalog_id(catalog_id)
    if not resolved:
        raise ValueError("Unknown or invalid catalog solution id.")

    pid, primary = resolved
    alignment_score = compute_alignment_score_1_4(
        need_domains=domains,
        need_objective=objective,
        need_impact=impact,
        primary=primary,
    )

    cases: list[dict[str, Any]] = [catalog_case_dict(pid, primary)]
    allowed_map: dict[str, dict[str, Any]] = {pid: cases[0]}
    for rp, rsol in _related_catalog_cases(pid, primary, domains):
        cdict = catalog_case_dict(rp, rsol)
        cases.append(cdict)
        allowed_map[rp] = cdict

    catalog_json = json.dumps(cases, ensure_ascii=False, indent=2)

    try:
        rsp = await llm_client.complete(
            prompt_name="business-impact-references",
            variables={
                "alignment_score": str(alignment_score),
                "catalog_cases_json": catalog_json,
                "need_pitch": pitch.strip() or "(not provided)",
                "need_domains": ", ".join(domains) if domains else "(not specified)",
                "need_objective": objective.strip() or "(not specified)",
                "need_impact": impact.strip() or "(not specified)",
                "explicit": (
                    "Summarise how the catalog records below support business impact relevance "
                    f"(alignment score is already fixed at {alignment_score} on a 1–4 scale)."
                ),
                "implicit": "Use only facts present in the JSON; do not add clients, metrics, or outcomes not listed.",
                "strategic": "Tie wording to sectors, deployments, objectives, and features exactly as given.",
            },
            response_format="json",
        )
        parsed = llm_client.parse_json_response(rsp)
    except Exception as exc:
        logger.warning("business-impact LLM step failed: %s", exc)
        return BusinessImpactScoreResponse(alignment_score=alignment_score, references=[])

    refs = _sanitize_references(parsed.get("references"), allowed_map)
    return BusinessImpactScoreResponse(alignment_score=alignment_score, references=refs)
