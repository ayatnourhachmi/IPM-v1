"""Business needs API endpoints."""

from __future__ import annotations

import asyncio
import json
import logging
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import llm_client
from app.core.config import settings
from app.core.langfuse_tracking import new_langfuse_client, safe_flush
from app.core.recommendation_limits import (
    MAX_KPIS_RECOMMENDATIONS,
    MAX_ORGANIZATIONAL_RECOMMENDATIONS,
    MAX_TECHNICAL_RECOMMENDATIONS,
)
from app.core.database import get_db
from app.core.embedding_client import embed_text_async
from app.models.business_need import BusinessNeed
from app.schemas.business_need import (
    AnalyzeRequest,
    AnalyzeResponse,
    BusinessNeedResponse,
    CatalogProduct,
    CatalogSearchResponse,
    Constraints,
    EvaluationScores,
    ExpertiseTeamEstimateRequest,
    ExpertiseTeamEstimateResponse,
    DurationEstimateRequest,
    DurationEstimateResponse,
    BusinessImpactScoreRequest,
    BusinessImpactScoreResponse,
    ExportReportRequest,
    CreateNeedRequest,
    GapAnalysisRequest,
    GapAnalysisResponse,
    OrganizationalRecommendation,
    RecommendationKPI,
    RecommendationsRequest,
    RecommendationsResponse,
    RiskItem,
    SolutionRecommendations,
    Tags,
    TagsConfidence,
    UpdateStatusRequest,
)


from app.core.pinecone_store import NS_DXC_CATALOG, namespace_vector_count, query_catalog
from app.services import embedding_service, id_service, nlp_service
from app.services.export_service import build_docx_report, build_pdf_report
from app.services.catalog_feature_match import (
    CATALOG_FETCH_CAP,
    CATALOG_RETURN_CAP,
    build_need_match_profile,
    catalog_row_matches_need,
)
from app.services.duration_formula import compute_duration
from app.services.business_impact_scoring import score_business_impact as run_business_impact_score
from app.services.expertise_team_service import estimate_expertise_team as run_expertise_team_estimate
from app.services.maturity_scoring import maturity_score, maturity_score_or_neutral
from app.services.validation_guards import (
    constrain_organizational_role,
    sanitize_organizational_recommendation,
    sanitize_pitch_tag_dict,
    sanitize_recommendation_kpi_triplet,
    sanitize_risk_fields,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/needs", tags=["needs"])


# ---------------------------------------------------------------------------
# Tag JSONB helpers — support both new {value, confidence} shape and legacy
# flat strings already persisted in the database.
# ---------------------------------------------------------------------------

def _tag_scalar(tags: dict, key: str, default: str = "") -> str:
    """Extract the string value from a scalar tag field (objectif / origine)."""
    raw = tags.get(key, default)
    if isinstance(raw, dict):
        return raw.get("value", default)
    return str(raw) if raw else default


def _tag_list(tags: dict, key: str) -> list[str]:
    """Extract a flat list of string values from a multi-value tag field (domaine / impact)."""
    raw = tags.get(key) or []
    if not isinstance(raw, list):
        return []
    result = []
    for item in raw:
        if isinstance(item, dict):
            v = item.get("value", "")
        else:
            v = str(item)
        if v:
            result.append(v)
    return result


def _default_tags() -> Tags:
    """Return a minimal valid Tags object used when a need has no tags stored."""
    return Tags(
        objectif={"value": "cost_reduction", "confidence": "low"},
        domaine=[{"value": "Autre", "confidence": "low"}],
        impact=[{"value": "Cost", "confidence": "low"}],
        origine={"value": "probleme_operationnel", "confidence": "low"},
    )


def _tags_from_db(raw: dict | None) -> Tags:
    """Load persisted tags safely — repair unknown enums/lists before constructing ``Tags``."""
    if not raw:
        return _default_tags()
    merged = {**_default_tags().model_dump(), **raw}
    cleaned = sanitize_pitch_tag_dict(merged)
    try:
        return Tags(**cleaned)
    except ValidationError as exc:
        logger.warning("Tags invalid after sanitization (%s); using defaults", exc)
        return _default_tags()


def _domains_match(solution_domain: str, need_domains: list[str]) -> bool:
    """Return True if solution_domain overlaps with any of the need domains.

    Matching is case-insensitive and bidirectional substring so that e.g.
    'Data Engineering' matches need domain 'Data', and 'Cloud' matches 'Cloud Infra'.
    'Autre' on either side is treated as a wildcard (always matches).
    """
    if not solution_domain:
        return True  # unknown domain → do not penalise
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


def _compress_solution_context(
    features: list[str],
    solution_domain: str,
    need_domains: list[str],
) -> tuple[list[str], bool]:
    """Drop solution features when the solution domain does not match the need domain.

    Returns (features_to_send, was_compressed).
    Compression removes irrelevant feature tokens before the LLM call.
    """
    if _domains_match(solution_domain, need_domains):
        return features, False
    logger.info(
        "Context compression: dropping %d features — solution domain '%s' "
        "does not match need domains %s",
        len(features),
        solution_domain,
        need_domains,
    )
    return [], True


def _gap_addressed_by_technical(technical: list[str], gap: str) -> bool:
    """Return True if some technical line clearly references the missing-capability text."""
    g = " ".join(gap.strip().lower().split())
    if not g:
        return True
    for line in technical:
        tl = " ".join(line.lower().split())
        if g in tl:
            return True
        if len(g) > 48 and g[:48] in tl:
            return True
    return False


def _ensure_technical_covers_missing_features(
    technical: list[str],
    features_missing: list[str],
    *,
    need_id_log: str = "",
    solution_id_log: str = "",
) -> list[str]:
    """Ensure each distinct features_missing has ≥1 technical recommendation (post-LLM)."""
    seen: set[str] = set()
    unique_missing: list[str] = []
    for raw in features_missing:
        m = str(raw).strip()
        if not m:
            continue
        key = m.lower()
        if key in seen:
            continue
        seen.add(key)
        unique_missing.append(m)

    synthetics: list[str] = []
    for gap in unique_missing:
        pool = technical + synthetics
        if _gap_addressed_by_technical(pool, gap):
            continue
        synthetics.append(
            f"Address the gap «{gap}»: define functional and non-functional requirements, "
            "select or build the missing capability, integrate it with dependent systems, "
            "and validate with acceptance tests before production rollout."
        )
        logger.info(
            "Recommendation mapping: synthetic technical line added for missing feature "
            "(need=%s solution=%s gap_preview=%r)",
            need_id_log,
            solution_id_log,
            gap[:80] + ("…" if len(gap) > 80 else ""),
        )

    max_technical = MAX_TECHNICAL_RECOMMENDATIONS
    tech_trimmed = list(technical)
    while len(synthetics) + len(tech_trimmed) > max_technical and tech_trimmed:
        tech_trimmed.pop()
    # Synthetics first so a hard cap (pathological many gaps) drops generic LLM lines, not gap coverage
    combined = synthetics + tech_trimmed
    if len(combined) > max_technical:
        logger.warning(
            "Recommendation mapping: truncating technical recommendations %d → %d "
            "(need=%s solution=%s); excess gap-specific lines dropped",
            len(combined),
            max_technical,
            need_id_log,
            solution_id_log,
        )
        combined = combined[:max_technical]
    return combined


def _parse_org_recommendation(raw: object) -> OrganizationalRecommendation | None:
    """Normalize LLM org output — dict {role, action}, legacy string, or partial dict."""
    if isinstance(raw, dict):
        role = str(raw.get("role", "") or "").strip()
        action = str(raw.get("action", "") or "").strip()
        if role and action:
            r2, a2 = sanitize_organizational_recommendation(role, action)
            return OrganizationalRecommendation(role=r2, action=a2)
        if action and not role:
            r2, a2 = sanitize_organizational_recommendation(
                "Implementation partner", action
            )
            return OrganizationalRecommendation(role=r2, action=a2)
        return None
    if isinstance(raw, str) and raw.strip():
        r2, a2 = sanitize_organizational_recommendation(
            "Implementation partner", raw.strip()
        )
        return OrganizationalRecommendation(role=r2, action=a2)
    return None


def _org_addresses_resource(
    organizational: list[OrganizationalRecommendation],
    resource: str,
) -> bool:
    """True if combined role/action text references the resource need phrase."""
    r = " ".join(resource.strip().lower().split())
    if not r:
        return True
    for row in organizational:
        blob = f"{row.role} {row.action}".lower()
        blob = " ".join(blob.split())
        if r in blob:
            return True
        if len(r) > 48 and r[:48] in blob:
            return True
    return False


def _infer_role_for_resource(resource: str) -> str:
    """Light heuristic for accountable role title from resource wording."""
    rl = resource.lower()
    triggers: tuple[tuple[tuple[str, ...], str], ...] = (
        (("machine learning", " ml", "prediction", "model", "nlp", "analytics "), "Data Scientist"),
        (("data engineer", "pipeline", "etl", "warehouse"), "Data Engineer"),
        (("integration", "api", "middleware", "kafka"), "Integration Engineer"),
        (("security", "compliance", "iam", "identity"), "Security / Compliance Analyst"),
        (("infra", "cloud", "kubernetes", "hosting"), "Platform / Infrastructure Engineer"),
        (("frontend", "ui ", "ux "), "Frontend Engineer"),
        (("backend", "microservice"), "Backend Engineer"),
        (("product owner", "business analyst", "stakeholder"), "Business Analyst"),
    )
    for keys, title in triggers:
        if any(k in rl for k in keys):
            return constrain_organizational_role(title)
    return constrain_organizational_role("Implementation lead")


def _ensure_org_covers_resources_needed(
    organizational: list[OrganizationalRecommendation],
    resources_needed: list[str],
    *,
    need_id_log: str = "",
    solution_id_log: str = "",
) -> list[OrganizationalRecommendation]:
    """Each distinct resources_needed gets ≥ one org row with role + action referencing it."""
    seen: set[str] = set()
    unique_res: list[str] = []
    for raw in resources_needed:
        x = str(raw).strip()
        if not x:
            continue
        k = x.lower()
        if k in seen:
            continue
        seen.add(k)
        unique_res.append(x)

    synthetics: list[OrganizationalRecommendation] = []
    for res in unique_res:
        pool = organizational + synthetics
        if _org_addresses_resource(pool, res):
            continue
        role = _infer_role_for_resource(res)
        synthetics.append(
            OrganizationalRecommendation(
                role=role,
                action=(
                    f"Own staffing and outcomes for «{res}»: define responsibilities, timelines, "
                    "and escalation path; confirm readiness before go-live."
                ),
            ),
        )
        logger.info(
            "Org recommendation mapping: synthetic role/action added for resource need "
            "(need=%s solution=%s preview=%r)",
            need_id_log,
            solution_id_log,
            res[:80] + ("…" if len(res) > 80 else ""),
        )

    max_org = MAX_ORGANIZATIONAL_RECOMMENDATIONS
    org_trimmed = list(organizational)
    while len(synthetics) + len(org_trimmed) > max_org and org_trimmed:
        org_trimmed.pop()
    combined = synthetics + org_trimmed
    if len(combined) > max_org:
        logger.warning(
            "Org recommendation mapping: truncating org rows %d → %d "
            "(need=%s solution=%s)",
            len(combined),
            max_org,
            need_id_log,
            solution_id_log,
        )
        combined = combined[:max_org]
    return combined


_PREREQUIS_TECH_FALLBACK: list[str] = [
    "Establish bounded proofs-of-value on the weakest integration assumptions before approving full engineering spend.",
    "Baseline data quality, lineage, and access prerequisites linked to Missing features above; publish owners and unblockers.",
    "Define explicit prerequisite exit criteria (what becomes true before a delivery plan is credible) keyed to gaps and IVI posture.",
    "Run stakeholder and dependency workshops across Microsoft / SAP / ServiceNow / AWS touchpoints referenced in Missing features.",
    "Document ITIL-aligned readiness checkpoints (who supports what in incident/change) before any pilot environment is treated as authoritative.",
]


_PREREQUIS_ORG_FALLBACK: list[OrganizationalRecommendation] = [
    OrganizationalRecommendation(
        role="Executive steering / portfolio",
        action=(
            "Gate funding and squad assignment on prerequisites; treat fit ≤4 as a discovery and readiness phase,"
            " not a locked go-live roadmap."
        ),
    ),
    OrganizationalRecommendation(
        role="Solution / product sponsorship",
        action=(
            "Validate problem–solution alignment and backlog scope with prerequisites closed in writing before scaling teams."
        ),
    ),
    OrganizationalRecommendation(
        role="Architecture and integration SMEs",
        action=(
            "Own closure of foundational unknowns across SAP, ServiceNow, AWS, and Microsoft estate "
            "integration points before committing build waves."
        ),
    ),
    OrganizationalRecommendation(
        role="Resource / workforce planning",
        action=(
            "Staff temporary prerequisite roles first (architecture, BA, SMEs); defer standing delivery Scrum capacity."
        ),
    ),
    OrganizationalRecommendation(
        role="Governance",
        action=(
            "Maintain a prerequisites register with RACI linking to incident/change process ownership per ITIL practice."
        ),
    ),
]



def _derive_constraints(tags: Tags) -> Constraints:
    """Build a typed Constraints object from a validated Tags instance."""
    return Constraints(
        domain=tags.domaine[0].value if tags.domaine else "Autre",
        impact=tags.impact[0].value if tags.impact else "Cost",
        objective=tags.objectif.value,
    )


def _constraints_from_db(need: BusinessNeed) -> Constraints:
    """Return stored constraints or derive them on-the-fly for legacy rows."""
    if need.constraints:
        return Constraints(**need.constraints)
    tags = _tags_from_db(need.tags)
    return _derive_constraints(tags)


def _confidence_from_tags(tags: Tags) -> dict | None:
    """Flatten tag confidences for the ``business_needs.confidence`` JSONB column."""
    d = tags.model_dump()
    out: dict[str, object] = {}
    obj = d.get("objectif")
    if isinstance(obj, dict) and obj.get("confidence") is not None:
        out["objectif"] = obj["confidence"]
    for key in ("domaine", "impact"):
        items = d.get(key) or []
        if isinstance(items, list) and items:
            stripped: list[dict[str, object]] = []
            for it in items:
                if isinstance(it, dict) and it.get("confidence") is not None:
                    stripped.append({"value": it.get("value"), "confidence": it["confidence"]})
            if stripped:
                out[key] = stripped
    orig = d.get("origine")
    if isinstance(orig, dict) and orig.get("confidence") is not None:
        out["origine"] = orig["confidence"]
    return out if out else None


def _risks_from_db(raw: object) -> list[RiskItem]:
    """Normalise persisted risks JSON to ``RiskItem`` models."""
    if not isinstance(raw, list):
        return []
    parsed: list[RiskItem] = []
    for r in raw:
        if isinstance(r, dict) and r.get("risk"):
            rz, sv = sanitize_risk_fields(
                str(r["risk"]), str(r.get("severity", "medium"))
            )
            parsed.append(RiskItem(risk=rz, severity=sv))
    return parsed


def _business_need_to_response(need: BusinessNeed) -> BusinessNeedResponse:
    """Map ORM row to API response including optional assessment fields."""
    return BusinessNeedResponse(
        id=need.id,
        pitch=need.pitch,
        horizon=need.horizon,
        tags=_tags_from_db(need.tags),
        confidence=need.confidence,
        constraints=_constraints_from_db(need),
        risks=_risks_from_db(need.risks),
        justifications=need.justifications,
        ivi_scores=need.ivi_scores,
        status=need.status,
        rework_note=need.rework_note,
        duplicate_matches=need.duplicate_matches or [],
        created_at=need.created_at,
        updated_at=need.updated_at,
    )


# ---------------------------------------------------------------------------
# Allowed status transitions
# ---------------------------------------------------------------------------
ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"submitted", "rework", "abandoned"},
    "submitted": {"in_qualification", "rework", "abandoned"},
    "in_qualification": {"selected", "rework", "abandoned"},
    "selected": {"delivery", "rework", "abandoned"},
    "rework": {"draft", "submitted"},
    "delivery": set(),          # terminal — Phase 2 may extend
    "abandoned": set(),         # terminal
}


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_pitch(request: AnalyzeRequest) -> AnalyzeResponse:
    """Analyze a pitch and return AI-generated tags and suggestions."""
    try:
        tags, suggestions = await nlp_service.analyze_pitch(
            request.pitch,
            horizon=request.horizon,
        )
        snap = _confidence_from_tags(tags)
        confidence_layer = TagsConfidence.model_validate(snap) if snap else None
        return AnalyzeResponse(
            tags=tags,
            suggestions=suggestions,
            constraints=_derive_constraints(tags),
            confidence=confidence_layer,
        )
    except Exception as exc:
        logger.error("Failed to analyze pitch: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="LLM analysis failed. Please try again.",
        ) from exc


@router.post("/expertise-team-estimate", response_model=ExpertiseTeamEstimateResponse)
async def estimate_expertise_team_ep(
    body: ExpertiseTeamEstimateRequest,
) -> ExpertiseTeamEstimateResponse:
    """Estimate a delivery team headcount-per-role constrained to ``allowed_roles``."""
    try:
        return await run_expertise_team_estimate(
            solution_description=body.solution_description,
            allowed_roles=list(body.allowed_roles),
        )
    except json.JSONDecodeError as exc:
        logger.error("expertise-team-estimate invalid JSON from LLM: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="LLM returned invalid JSON for team estimate.",
        ) from exc
    except Exception as exc:
        logger.error("expertise-team-estimate failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Expertise estimation failed. Please try again.",
        ) from exc


@router.post("/duration-estimate", response_model=DurationEstimateResponse)
async def estimate_duration_ep(body: DurationEstimateRequest) -> DurationEstimateResponse:
    """Estimate calendar duration and IVI-aligned duration score from gaps, staffing, maturity."""
    n_missing = len(body.features_missing)
    est = compute_duration(
        features_missing_count=n_missing,
        team_size=body.team_size,
        maturity=body.maturity.strip(),
    )
    return DurationEstimateResponse(
        duration_months=est.duration_months,
        duration_score=est.duration_score,
    )


@router.post("/business-impact-score", response_model=BusinessImpactScoreResponse)
async def business_impact_score_ep(body: BusinessImpactScoreRequest) -> BusinessImpactScoreResponse:
    """Rules-based impact alignment plus LLM narration restricted to catalogue facts."""
    catalog_id = str(body.selected_solution.get("id", "")).strip()
    try:
        return await run_business_impact_score(
            pitch=body.pitch,
            domains=list(body.domains),
            objective=body.objective,
            impact=body.impact,
            catalog_id=catalog_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc) or "Invalid catalog reference.",
        ) from exc


@router.post("", response_model=BusinessNeedResponse, status_code=status.HTTP_201_CREATED)
async def create_need(
    request: CreateNeedRequest,
    db: AsyncSession = Depends(get_db),
) -> BusinessNeedResponse:
    """Create a new business need with AI enrichment and duplicate detection."""
    try:
        # 1. Tags + optional embeddings — Pinecone duplicate search (when configured).
        if settings.pinecone_configured:
            if request.tags is not None:
                tags = request.tags
                embedding = await embed_text_async(request.pitch, is_query=False)
            else:
                (tags, _suggestions), embedding = await asyncio.gather(
                    nlp_service.analyze_pitch(request.pitch),
                    embed_text_async(request.pitch, is_query=False),
                )
        else:
            if request.tags is not None:
                tags = request.tags
            else:
                tags, _suggestions = await nlp_service.analyze_pitch(request.pitch)

        # 2. Generate unique ID
        need_id = await id_service.generate_id(db)

        # 3. Upsert + duplicate search (skipped when Pinecone env is not set).
        if settings.pinecone_configured:
            _, duplicates = await asyncio.gather(
                asyncio.to_thread(
                    embedding_service.upsert_embedding,
                    need_id, request.pitch, "draft", embedding,
                ),
                asyncio.to_thread(
                    embedding_service.search_duplicates,
                    request.pitch, need_id, embedding,
                ),
            )
        else:
            duplicates = []

        # 4. Persist to PostgreSQL
        constraints = _derive_constraints(tags)
        need = BusinessNeed(
            id=need_id,
            pitch=request.pitch,
            horizon=request.horizon,
            tags=tags.model_dump(),
            confidence=_confidence_from_tags(tags),
            constraints=constraints.model_dump(),
            status="draft",
            duplicate_matches=[d.model_dump() for d in duplicates],
        )
        db.add(need)
        await db.flush()
        await db.refresh(need)

        return _business_need_to_response(need)

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to create business need: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create business need: {str(exc)}",
        ) from exc


@router.get("", response_model=list[BusinessNeedResponse])
async def list_needs(
    db: AsyncSession = Depends(get_db),
) -> list[BusinessNeedResponse]:
    """Return all business needs ordered by creation date descending."""
    try:
        result = await db.execute(
            select(BusinessNeed).order_by(BusinessNeed.created_at.desc())
        )
        needs = result.scalars().all()

        return [_business_need_to_response(n) for n in needs]
    except Exception as exc:
        logger.error("Failed to list business needs: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve business needs.",
        ) from exc


@router.get("/{need_id}", response_model=BusinessNeedResponse)
async def get_need(
    need_id: str,
    db: AsyncSession = Depends(get_db),
) -> BusinessNeedResponse:
    """Return a specific business need by ID."""
    try:
        result = await db.execute(
            select(BusinessNeed).where(BusinessNeed.id == need_id)
        )
        need = result.scalar_one_or_none()

        if need is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Business need '{need_id}' not found.",
            )

        return _business_need_to_response(need)

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to retrieve business need %s: %s", need_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve business need.",
        ) from exc


@router.patch("/{need_id}/status", response_model=BusinessNeedResponse)
async def update_status(
    need_id: str,
    request: UpdateStatusRequest,
    db: AsyncSession = Depends(get_db),
) -> BusinessNeedResponse:
    """Update the status of a business need, enforcing the transition rules."""
    try:
        result = await db.execute(
            select(BusinessNeed).where(BusinessNeed.id == need_id)
        )
        need = result.scalar_one_or_none()

        if need is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Business need '{need_id}' not found.",
            )

        # Enforce transition rules
        allowed = ALLOWED_TRANSITIONS.get(need.status, set())
        if request.status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Cannot transition from '{need.status}' to '{request.status}'. "
                       f"Allowed transitions: {sorted(allowed) if allowed else 'none'}.",
            )

        # Apply the update
        need.status = request.status
        if request.status == "rework" and request.note:
            need.rework_note = request.note
        elif request.status == "submitted":
            need.rework_note = None

        await db.flush()
        await db.refresh(need)

        # Refresh Pinecone vector metadata (pitch/status)
        try:
            embedding_service.upsert_embedding(need.id, need.pitch, need.status)
        except Exception as vec_exc:
            logger.warning("Failed to update Pinecone vector for %s: %s", need.id, vec_exc)

        return _business_need_to_response(need)

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to update status for %s: %s", need_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update business need status.",
        ) from exc


@router.post("/{need_id}/catalog-search", response_model=CatalogSearchResponse)
async def catalog_search(
    need_id: str,
    db: AsyncSession = Depends(get_db),
) -> CatalogSearchResponse:
    """Return up to five DXC catalog products similar to the need with ≥1 overlapping catalogue feature."""
    try:
        result = await db.execute(
            select(BusinessNeed).where(BusinessNeed.id == need_id)
        )
        need = result.scalar_one_or_none()

        if need is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Business need '{need_id}' not found.",
            )

        if not settings.pinecone_configured:
            logger.info("Pinecone not configured — returning empty catalog results for %s", need_id)
            return CatalogSearchResponse(results=[], total=0)

        # Build query text from pitch + AI-derived fields
        tags: dict = need.tags or {}

        OBJECTIF_LABELS = {
            "cost_reduction": "cost reduction efficiency savings",
            "cx_improvement": "customer experience improvement satisfaction",
            "risk_mitigation": "risk management compliance security",
            "market_opportunity": "market growth revenue expansion",
            "productivity": "productivity automation efficiency",
            "innovation": "innovation digital transformation modernization",
        }
        objectif_str = OBJECTIF_LABELS.get(_tag_scalar(tags, "objectif"), "")

        domains_list: list[str] = _tag_list(tags, "domaine")
        domains_str = " ".join(domains_list)

        impact_parts: list[str] = _tag_list(tags, "impact")
        impact_str = " ".join(impact_parts)

        match_profile = build_need_match_profile(
            pitch=need.pitch,
            objectif_str=objectif_str,
            domains_list=domains_list,
            impact_parts=impact_parts,
        )

        query_text = " ".join(
            filter(None, [need.pitch, objectif_str, domains_str, impact_str])
        )
        query_text = query_text[:600].strip()

        # Embed — is_query=True applies the BGE retrieval prefix
        embedding = await embed_text_async(query_text, is_query=True)

        pool = min(
            CATALOG_FETCH_CAP,
            max(1, namespace_vector_count(NS_DXC_CATALOG)),
        )
        pine_rows = query_catalog(embedding, top_k=pool)

        def _meta_val(meta: dict, key: str) -> str | None:
            v = meta.get(key)
            return None if (v is None or v == "") else str(v)

        def _meta_list(meta: dict, key: str) -> list[str]:
            raw = meta.get(key, "")
            if not raw:
                return []
            return [item.strip() for item in str(raw).split(",") if item.strip()]

        products: list[CatalogProduct] = []
        for pid, meta, doc, cosine_sim in pine_rows:
            score = round(max(0.0, min(1.0, cosine_sim)), 2)
            maturity = _meta_val(meta, "maturity")
            products.append(CatalogProduct(
                id=pid,
                name=meta.get("name", ""),
                description=doc,
                domain=_meta_val(meta, "domain"),
                target_objective=_meta_val(meta, "target_objective"),
                maturity=maturity,
                maturity_level=maturity,
                client_sectors=_meta_list(meta, "client_sectors"),
                complexity=_meta_val(meta, "complexity"),
                ipm_stage=_meta_val(meta, "ipm_stage"),
                features=_meta_list(meta, "features"),
                limitations=_meta_list(meta, "limitations"),
                relevance_score=score,
            ))

        products = [
            p
            for p in products
            if catalog_row_matches_need(
                p.features,
                p.description or "",
                p.name or "",
                profile=match_profile,
            )
        ]
        products.sort(key=lambda p: p.relevance_score, reverse=True)
        products = products[:CATALOG_RETURN_CAP]

        return CatalogSearchResponse(results=products, total=len(products))

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to run catalog search for %s: %s", need_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Catalog search failed. Please try again.",
        ) from exc


@router.post("/{need_id}/gap-analysis", response_model=GapAnalysisResponse)
async def gap_analysis(
    need_id: str,
    body: GapAnalysisRequest,
    db: AsyncSession = Depends(get_db),
) -> GapAnalysisResponse:
    """Run a structured gap analysis between a business need and a selected DXC solution."""
    try:
        result = await db.execute(
            select(BusinessNeed).where(BusinessNeed.id == need_id)
        )
        need = result.scalar_one_or_none()

        if need is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Business need '{need_id}' not found.",
            )

        # Extract solution fields from request body
        sol = body.selected_solution.model_dump()
        name: str = sol.get("name", "Unknown")
        description: str = sol.get("description", "") or ""
        features_raw = sol.get("features", [])
        features: list[str] = features_raw if isinstance(features_raw, list) else []
        business_impact: str = sol.get("business_impact", "") or ""
        # Accept both Excel field ("maturity") and legacy alias ("maturity_level")
        maturity_level: str = sol.get("maturity") or sol.get("maturity_level") or ""
        complexity: str = sol.get("complexity", "") or ""
        domain: str = sol.get("domain", "") or ""

        # Extract need context from JSONB tags
        need_tags: dict = need.tags or {}
        objectif: str = _tag_scalar(need_tags, "objectif") or "Not specified"
        impact_list: list[str] = _tag_list(need_tags, "impact")
        impact: str = ", ".join(impact_list) if impact_list else "Not specified"
        domains_list: list[str] = _tag_list(need_tags, "domaine")
        domains: str = ", ".join(domains_list) if domains_list else "Not specified"

        # Context compression — drop features when solution domain doesn't match need
        features, _compressed = _compress_solution_context(features, domain, domains_list)

        # Load typed constraints (stored at creation time; fall back for legacy rows)
        constraints = _constraints_from_db(need)
        constraints_str = (
            f"objective={constraints.objective}, "
            f"domain={constraints.domain}, "
            f"impact={constraints.impact}"
        )

        variables: dict[str, str] = {
            "pitch": need.pitch,
            "objectif": objectif,
            "impact": impact,
            "domains": domains,
            "constraints": constraints_str,
            "solution_name": name,
            "solution_description": description,
            "solution_features": ", ".join(features) if features else "Not listed",
            "solution_business_impact": business_impact or "Not specified",
            "solution_maturity": maturity_level or "Not specified",
            "solution_complexity": complexity or "Not specified",
            "solution_domain": domain or "Not specified",
        }

        gap_trace_meta = {
            "endpoint": "gap-analysis",
            "need_id": need_id,
            "solution_id": sol.get("id", "unknown"),
            "solution_name": name,
        }
        # Langfuse trace — create before LLM; generation attached inside llm_client.complete
        _lf = new_langfuse_client()
        _lf_trace = None
        if _lf is not None:
            try:
                _lf_trace = _lf.trace(
                    name="gap-analysis",
                    input={
                        "need_id": need_id,
                        "need_pitch": need.pitch,
                        "solution_name": name,
                        "solution_maturity": maturity_level,
                    },
                    metadata=gap_trace_meta,
                )
            except Exception:
                pass

        # LLM call — replicates nlp_service.py pattern
        llm_response = await llm_client.complete(
            prompt_name="gap-analysis",
            variables={
                **variables,
                "explicit": "Perform a structured gap analysis between the business need and the proposed solution.",
                "implicit": "Identify overlaps, gaps, and practical requirements for implementation.",
                "strategic": "Highlight DXC's expertise and position DXC as trusted delivery partner."
            },
            response_format="json",
            lf_parent_trace=_lf_trace,
        )

        # Parse
        try:
            parsed = llm_client.parse_json_response(llm_response)
        except Exception as parse_exc:
            logger.error("Gap analysis JSON parse failed for %s: %s", need_id, parse_exc)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="LLM returned invalid JSON for gap analysis",
            ) from parse_exc

        features_matching: list[str] = parsed.get("features_matching") or []
        features_missing: list[str] = parsed.get("features_missing") or []
        resources_needed: list[str] = parsed.get("resources_needed") or []
        fit_score: int = max(1, min(10, int(parsed.get("fit_score", 5))))
        fit_justification: str = str(parsed.get("fit_justification") or "")

        risks: list[RiskItem] = []
        for r in (parsed.get("risks") or []):
            if isinstance(r, dict) and r.get("risk"):
                rz, sv = sanitize_risk_fields(
                    str(r["risk"]), str(r.get("severity", "medium"))
                )
                risks.append(RiskItem(risk=rz, severity=sv))

        # Prefer AI-generated qualification criteria when provided.
        # If missing (e.g., outdated prompt), derive deterministic scores from the
        # structured gap output so evaluation remains automatic and stable.
        def _clamp_score_5(value: float) -> int:
            return max(1, min(5, int(round(value))))

        def _score_value(raw: object, fallback: float) -> int:
            try:
                return _clamp_score_5(float(raw))
            except (TypeError, ValueError):
                return _clamp_score_5(fallback)

        ai_scores = parsed.get("evaluation_scores") if isinstance(parsed, dict) else None
        if isinstance(ai_scores, dict):
            maturite_eval = _score_value(ai_scores.get("maturite"), 3)
            maturite_just = str(ai_scores.get("maturite_justification") or "")
            expertise_eval = _score_value(ai_scores.get("expertise"), 3)
            expertise_just = str(ai_scores.get("expertise_justification") or "")
            duree_eval     = _score_value(ai_scores.get("duree"), 3)
            duree_just     = str(ai_scores.get("duree_justification") or "")
            impact_eval    = _score_value(ai_scores.get("impact"), fit_score / 2)
            impact_just    = str(ai_scores.get("impact_justification") or "")
        else:
            matching  = len(features_matching)
            missing   = len(features_missing)
            resources = len(resources_needed)

            # Maturité from catalog maturity column only (maturity scoring engine)
            maturite_eval = maturity_score_or_neutral(maturity_level, neutral=3)
            # Expertise: more matching features → higher DXC expertise signal
            expertise_eval = _clamp_score_5(2 + matching * 0.5)
            # Durée: fewer gaps and required resources → faster delivery
            duree_eval     = _clamp_score_5(5 - (resources * 0.5) - (missing * 0.3))
            # Impact: direct proxy from fit_score
            impact_eval    = _clamp_score_5(fit_score / 2)

            maturite_just = expertise_just = duree_just = impact_just = ""

        # Catalog-only maturité: overwrite LLM / heuristic when label maps cleanly
        calibration_steps: list[dict] = []
        _catalog_maturite = maturity_score(maturity_level)
        if _catalog_maturite is not None:
            if maturite_eval != _catalog_maturite:
                logger.info(
                    "Maturity scoring engine: maturité %s → %s from catalog maturity %r",
                    maturite_eval,
                    _catalog_maturite,
                    maturity_level,
                )
                calibration_steps.append(
                    {
                        "step": "catalog_maturity_alignment",
                        "catalog_maturity_label": maturity_level,
                        "maturite_before": maturite_eval,
                        "maturite_after": _catalog_maturite,
                    },
                )
            maturite_eval = _catalog_maturite

        # ── Post-LLM score calibration rules ──────────────────────────────────
        fit_score_before_cap = fit_score
        if len(features_missing) > len(features_matching) and fit_score > 5:
            logger.info(
                "Calibration [missing>matching]: fit_score capped %d → 5 "
                "(missing=%d, matching=%d)",
                fit_score, len(features_missing), len(features_matching),
            )
            calibration_steps.append(
                {
                    "step": "missing_features_exceed_matching_fit_cap",
                    "fit_score_before": fit_score_before_cap,
                    "fit_score_after": 5,
                    "features_missing": len(features_missing),
                    "features_matching": len(features_matching),
                },
            )
            fit_score = 5

        # ──────────────────────────────────────────────────────────────────────

        try:
            if _lf_trace:
                final_meta = dict(gap_trace_meta)
                if calibration_steps:
                    final_meta["score_calibration"] = calibration_steps
                _lf_trace.update(
                    output={
                        "fit_score": fit_score,
                        "fit_score_llm_raw": fit_score_before_cap,
                        "features_matching_count": len(features_matching),
                        "features_missing_count": len(features_missing),
                        "resources_needed_count": len(resources_needed),
                        "evaluation_ivi": {
                            "maturite": maturite_eval,
                            "expertise": expertise_eval,
                            "duree": duree_eval,
                            "impact": impact_eval,
                        },
                    },
                    metadata=final_meta,
                )
            safe_flush(_lf)
        except Exception:
            pass

        evaluation = EvaluationScores(
            maturite=maturite_eval,
            maturite_justification=maturite_just,
            expertise=expertise_eval,
            expertise_justification=expertise_just,
            duree=duree_eval,
            duree_justification=duree_just,
            impact=impact_eval,
            impact_justification=impact_just,
        )
        need.risks = [r.model_dump() for r in risks]
        need.justifications = {
            "maturite_justification": maturite_just,
            "expertise_justification": expertise_just,
            "duree_justification": duree_just,
            "impact_justification": impact_just,
            "fit_justification": fit_justification,
        }
        need.ivi_scores = {
            "maturite": maturite_eval,
            "expertise": expertise_eval,
            "duree": duree_eval,
            "impact": impact_eval,
        }
        await db.flush()

        return GapAnalysisResponse(
            features_matching=features_matching,
            features_missing=features_missing,
            resources_needed=resources_needed,
            risks=risks,
            fit_score=fit_score,
            fit_justification=fit_justification,
            evaluation_scores=evaluation,
            solution_name=name,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Gap analysis failed for %s: %s", need_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gap analysis failed. Please try again.",
        ) from exc


@router.post("/{need_id}/recommendations", response_model=RecommendationsResponse)
async def generate_recommendations(
    need_id: str,
    body: RecommendationsRequest,
    db: AsyncSession = Depends(get_db),
) -> RecommendationsResponse:
    """Generate delivery recommendations per selected solution."""
    try:
        result = await db.execute(
            select(BusinessNeed).where(BusinessNeed.id == need_id)
        )
        need = result.scalar_one_or_none()

        if need is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Business need '{need_id}' not found.",
            )

        if not body.selected_solutions:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="At least one selected solution is required.",
            )

        need_tags: dict = need.tags or {}
        objectif: str = _tag_scalar(need_tags, "objectif") or "Not specified"
        impact_list: list[str] = _tag_list(need_tags, "impact")
        impact: str = ", ".join(impact_list) if impact_list else "Not specified"
        domains_list: list[str] = _tag_list(need_tags, "domaine")
        domains: str = ", ".join(domains_list) if domains_list else "Not specified"

        def _as_list(value: object) -> list[str]:
            if isinstance(value, list):
                return [str(v).strip() for v in value if str(v).strip()]
            return []

        def _safe_int(value: object, default: int) -> int:
            try:
                return int(value)
            except (TypeError, ValueError):
                return default

        async def _recommend_for_solution(sol: dict) -> SolutionRecommendations:
            solution_id = str(sol.get("id", "unknown"))
            solution_name = str(sol.get("name", "Unknown solution"))
            description = str(sol.get("description", "") or "")
            features = _as_list(sol.get("features"))
            business_impact = str(sol.get("business_impact", "") or "")
            # Accept both Excel field ("maturity") and legacy alias ("maturity_level")
            maturity_level = str(sol.get("maturity") or sol.get("maturity_level") or "")
            complexity = str(sol.get("complexity", "") or "")
            domain = str(sol.get("domain", "") or "")

            # Context compression — reuse need domains already extracted in outer scope
            features, _ = _compress_solution_context(features, domain, domains_list)

            gap = sol.get("gap_analysis") if isinstance(sol.get("gap_analysis"), dict) else {}
            features_matching = _as_list(gap.get("features_matching")) if isinstance(gap, dict) else []
            features_missing = _as_list(gap.get("features_missing")) if isinstance(gap, dict) else []
            resources_needed = _as_list(gap.get("resources_needed")) if isinstance(gap, dict) else []
            fit_score = _safe_int(gap.get("fit_score") if isinstance(gap, dict) else None, 5)

            evaluation_scores = sol.get("evaluation_scores")
            if not isinstance(evaluation_scores, dict) and isinstance(gap, dict):
                evaluation_scores = gap.get("evaluation_scores")
            if not isinstance(evaluation_scores, dict):
                evaluation_scores = {}

            fit_justification = str(gap.get("fit_justification") or "") if isinstance(gap, dict) else ""

            fit_clamped = max(1, min(10, fit_score))
            rec_mode = "PREREQUIS" if fit_clamped <= 4 else "STANDARD"
            if rec_mode == "PREREQUIS":
                logger.info(
                    "Recommendations PREREQUIS mode (fit_score=%s) need=%s solution=%s",
                    fit_clamped,
                    need_id,
                    solution_id,
                )
                mode_instructions = (
                    "PREREQUIS MODE: Gap fit score is 4 or lower on a 1–10 scale. Do NOT present the output primarily as a "
                    "go-live delivery roadmap, multi-wave rollout calendar, or steady-state operations cutover. Treat the whole "
                    "JSON as prerequisites and readiness gates: technical lines are foundations, spikes, baselines, integrations "
                    "clarity, unknowns closure, and risk retirement. Organizational lines are staffing, sponsorship, portfolio, "
                    "and governance prerequisites. KPIs evidence prerequisite completion and gated decisions (exit criteria), "
                    "not production KPIs that assume fit is already adequate."
                )
                explicit = (
                    "PREREQUIS mode: prerequisites and readiness only — fit is weak; defer delivery-plan center of gravity."
                )
                implicit = (
                    "Prefer discovery, proof-of-value, feasibility closes, and stakeholder decision points over build/scale language."
                )
            else:
                mode_instructions = (
                    "Mode STANDARD: Fit score is above the PREREQUIS threshold — recommendations may include pragmatic "
                    "implementation and delivery trajectory while still honoring ecosystem anchoring and mandatory missing-feature "
                    "and resource coverage rules."
                )
                explicit = (
                    "Generate actionable technical, organizational, and KPI recommendations for the selected solution."
                )
                implicit = (
                    "Ensure recommendations are concrete, enterprise-ready, and implementation-focused."
                )

            variables: dict[str, str] = {
                "pitch": need.pitch,
                "objectif": objectif,
                "impact": impact,
                "domains": domains,
                "solution_name": solution_name,
                "solution_description": description or "Not specified",
                "solution_features": ", ".join(features) if features else "Not listed",
                "solution_business_impact": business_impact or "Not specified",
                "solution_maturity": maturity_level or "Not specified",
                "solution_complexity": complexity or "Not specified",
                "solution_domain": domain or "Not specified",
                "features_matching": ", ".join(features_matching) if features_matching else "Not specified",
                "features_missing": ", ".join(features_missing) if features_missing else "Not specified",
                "resources_needed": ", ".join(resources_needed) if resources_needed else "Not specified",
                "fit_score": str(fit_clamped),
                "fit_justification": fit_justification or "Not specified",
                "eval_maturite": str(max(1, min(5, _safe_int(evaluation_scores.get("maturite"), 3)))),
                "eval_expertise": str(max(1, min(5, _safe_int(evaluation_scores.get("expertise"), 3)))),
                "eval_duree":     str(max(1, min(5, _safe_int(evaluation_scores.get("duree"), 3)))),
                "eval_impact":    str(max(1, min(5, _safe_int(evaluation_scores.get("impact"), 3)))),
                "eval_maturite_justification":  str(evaluation_scores.get("maturite_justification") or ""),
                "eval_expertise_justification": str(evaluation_scores.get("expertise_justification") or ""),
                "eval_duree_justification":     str(evaluation_scores.get("duree_justification") or ""),
                "eval_impact_justification":    str(evaluation_scores.get("impact_justification") or ""),
                "recommendation_mode": rec_mode,
                "mode_instructions": mode_instructions,
            }

            technical: list[str] = []
            organizational: list[OrganizationalRecommendation] = []
            kpis: list[RecommendationKPI] = []

            _rec_lf = new_langfuse_client()
            _rec_trace = None
            if _rec_lf is not None:
                try:
                    _rec_trace = _rec_lf.trace(
                        name="solution-recommendations",
                        input={
                            "need_id": need_id,
                            "solution_id": solution_id,
                            "solution_name": solution_name[:120],
                        },
                        metadata={
                            "fit_score": fit_clamped,
                            "recommendation_mode": rec_mode,
                        },
                    )
                except Exception:
                    pass

            try:
                llm_response = await llm_client.complete(
                    prompt_name="solution-recommendations",
                    variables={
                        **variables,
                        "explicit": explicit,
                        "implicit": implicit,
                        "strategic": "Reinforce DXC's value as a trusted delivery partner.",
                        "dxc_context": json.dumps(DXC_CONTEXT)
                    },
                    response_format="json",
                    lf_parent_trace=_rec_trace,
                )
                parsed = llm_client.parse_json_response(llm_response)

                if isinstance(parsed, dict):
                    tech_raw = parsed.get("technical_recommendations")
                    org_raw = parsed.get("organizational_recommendations")
                    kpi_raw = parsed.get("kpis")

                    if isinstance(tech_raw, list):
                        technical = [str(item).strip() for item in tech_raw if str(item).strip()]
                    if isinstance(org_raw, list):
                        for item in org_raw:
                            row = _parse_org_recommendation(item)
                            if row:
                                organizational.append(row)
                    if isinstance(kpi_raw, list):
                        for item in kpi_raw:
                            if not isinstance(item, dict):
                                continue
                            name = str(item.get("name", "")).strip()
                            target = str(item.get("target", "")).strip()
                            criteria = str(item.get("measurement_criteria", "")).strip()
                            if not (name or target or criteria):
                                continue
                            n, t, c = sanitize_recommendation_kpi_triplet(
                                name, target, criteria, mode=rec_mode
                            )
                            kpis.append(
                                RecommendationKPI(
                                    name=n,
                                    target=t,
                                    measurement_criteria=c,
                                )
                            )
            except Exception as rec_exc:
                logger.warning("Recommendations generation failed for %s/%s: %s", need_id, solution_id, rec_exc)
            finally:
                safe_flush(_rec_lf)

            if not technical:
                if rec_mode == "PREREQUIS":
                    technical = list(_PREREQUIS_TECH_FALLBACK)
                else:
                    technical = [
                        "Define a target architecture and integration blueprint across core systems.",
                        "Prioritize API contracts and data mappings for critical business flows.",
                        "Plan dependencies and phased rollout milestones to reduce delivery risk.",
                        "Set data quality controls and monitoring for production readiness.",
                        "Track top technical risks with mitigation owners and trigger thresholds.",
                    ]

            technical = _ensure_technical_covers_missing_features(
                technical,
                features_missing,
                need_id_log=need_id,
                solution_id_log=solution_id,
            )

            if not organizational:
                if rec_mode == "PREREQUIS":
                    organizational = list(_PREREQUIS_ORG_FALLBACK)
                else:
                    organizational = [
                    OrganizationalRecommendation(
                        role="Program / delivery leadership",
                        action=(
                            "Assign an accountable product owner, solution architect, and implementation "
                            "lead with clear RACI for scope, dependencies, and go-live readiness."
                        ),
                    ),
                    OrganizationalRecommendation(
                        role="Resource management",
                        action=(
                            "Define required profiles, workload, and phased capacity commitments by squad "
                            "against the delivery backlog."
                        ),
                    ),
                    OrganizationalRecommendation(
                        role="Governance",
                        action=(
                            "Establish steering cadence, decision rights, escalation paths, and compliance "
                            "checkpoints aligned to enterprise policies."
                        ),
                    ),
                    OrganizationalRecommendation(
                        role="Change adoption",
                        action=(
                            "Publish training, stakeholder communications, and adoption metrics with owners "
                            "for each rollout wave."
                        ),
                    ),
                    OrganizationalRecommendation(
                        role="Security / risk",
                        action=(
                            "Validate security assessments, DPIA/IRP touchpoints where applicable, "
                            "and operational handover readiness before production."
                        ),
                    ),
                ]

            organizational = _ensure_org_covers_resources_needed(
                organizational,
                resources_needed,
                need_id_log=need_id,
                solution_id_log=solution_id,
            )
            if not kpis:
                if rec_mode == "PREREQUIS":
                    kpis = [
                        RecommendationKPI(
                            name="Prerequisite register completeness",
                            target=(
                                "100% of critical gaps and resources-needed items mapped to an owning "
                                "role and dated exit criterion"
                            ),
                            measurement_criteria=(
                                "Tracked artifact reviewed in steering (portfolio tool, ServiceNow, or equivalent)"
                            ),
                        ),
                        RecommendationKPI(
                            name="Executive go/no-go prereq checkpoint",
                            target="Formal decision logged after POC or spike artifacts are accepted",
                            measurement_criteria="Steering minute or portfolio record referencing evidence pack",
                        ),
                        RecommendationKPI(
                            name="Integration unknowns retired",
                            target=(
                                "No more than three open critical integration unknowns before staffing "
                                "a committed build trajectory"
                            ),
                            measurement_criteria=(
                                "Architecture decision log referencing Microsoft, SAP, ServiceNow, or AWS "
                                "touchpoints where applicable"
                            ),
                        ),
                    ]
                else:
                    kpis = [
                        RecommendationKPI(
                            name="Time-to-value",
                            target="First measurable business outcome within 12 weeks",
                            measurement_criteria="Track weeks from project kickoff to first KPI uplift",
                        ),
                        RecommendationKPI(
                            name="Adoption rate",
                            target=">= 75% active usage among target users by quarter 1",
                            measurement_criteria="Monthly active users divided by targeted users",
                        ),
                        RecommendationKPI(
                            name="Operational impact",
                            target=">= 20% improvement on the primary operational metric",
                            measurement_criteria="Baseline vs post-go-live metric delta",
                        ),
                    ]

            return SolutionRecommendations(
                solution_id=solution_id,
                solution_name=solution_name,
                mode=rec_mode,
                technical_recommendations=technical[:MAX_TECHNICAL_RECOMMENDATIONS],
                organizational_recommendations=organizational[
                    :MAX_ORGANIZATIONAL_RECOMMENDATIONS
                ],
                kpis=kpis[:MAX_KPIS_RECOMMENDATIONS],
            )

        recommendations = await asyncio.gather(
            *[_recommend_for_solution(s.model_dump()) for s in body.selected_solutions]
        )

        return RecommendationsResponse(recommendations=list(recommendations))

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Recommendations generation failed for %s: %s", need_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate recommendations. Please try again.",
        ) from exc


@router.post("/{need_id}/export/pdf")
async def export_pdf(
    need_id: str,
    body: ExportReportRequest,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Generate and stream a professional PDF report."""
    try:
        result = await db.execute(select(BusinessNeed).where(BusinessNeed.id == need_id))
        need = result.scalar_one_or_none()
        if need is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Business need '{need_id}' not found.",
            )

        pdf_bytes = build_pdf_report(
            need_id=need_id,
            pitch=need.pitch,
            recommendations=[item.model_dump() for item in body.recommendations],
            delivery_solutions=[item.model_dump() for item in body.delivery_solutions],
        )

        filename = f"{need_id.lower()}-recommendations.pdf"
        return StreamingResponse(
            BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("PDF export failed for %s: %s", need_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate PDF report.",
        ) from exc


@router.post("/{need_id}/export/docx")
async def export_docx(
    need_id: str,
    body: ExportReportRequest,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Generate and stream a professional DOCX report."""
    try:
        result = await db.execute(select(BusinessNeed).where(BusinessNeed.id == need_id))
        need = result.scalar_one_or_none()
        if need is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Business need '{need_id}' not found.",
            )

        docx_bytes = build_docx_report(
            need_id=need_id,
            pitch=need.pitch,
            recommendations=[item.model_dump() for item in body.recommendations],
            delivery_solutions=[item.model_dump() for item in body.delivery_solutions],
        )

        filename = f"{need_id.lower()}-recommendations.docx"
        return StreamingResponse(
            BytesIO(docx_bytes),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("DOCX export failed for %s: %s", need_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate DOCX report.",
        ) from exc
