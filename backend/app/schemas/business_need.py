"""Pydantic v2 request / response schemas for the business needs API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, Literal, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Confidence-scored tag primitives
# ---------------------------------------------------------------------------

Confidence = Literal["low", "medium", "high"]

T = TypeVar("T")


class TagField(BaseModel, Generic[T]):
    """A single scalar tag value with an associated AI confidence level."""

    value: T
    confidence: Confidence


class TagItem(BaseModel):
    """A single item in a multi-value tag list, with its own confidence level."""

    value: str
    confidence: Confidence


# ---------------------------------------------------------------------------
# Nested schemas
# ---------------------------------------------------------------------------

class Tags(BaseModel):
    """AI-generated metadata tags for a business need."""

    objectif: TagField[Literal[
        "cost_reduction", "cx_improvement", "risk_mitigation", "market_opportunity"
    ]] = Field(description="Primary objective classification with confidence")
    domaine: list[TagItem] = Field(description="Business domains, each with confidence")
    impact: list[TagItem] = Field(description="Impact areas, each with confidence")
    origine: TagField[Literal[
        "enjeu_marche", "probleme_operationnel", "demande_client"
    ]] = Field(description="Origin classification with confidence")

    @field_validator("objectif", "origine", mode="before")
    @classmethod
    def _coerce_scalar(cls, v: object) -> object:
        """Accept legacy flat strings from old DB rows; wrap them with low confidence."""
        if isinstance(v, str):
            return {"value": v, "confidence": "low"}
        return v

    @field_validator("domaine", "impact", mode="before")
    @classmethod
    def _coerce_list(cls, v: object) -> object:
        """Accept legacy flat string lists from old DB rows; wrap each with low confidence."""
        if isinstance(v, list):
            return [
                {"value": item, "confidence": "low"} if isinstance(item, str) else item
                for item in v
            ]
        return v


class TagsConfidence(BaseModel):
    """Flattened per-dimension classification confidence aligned with Tags (analyze / persistence aid)."""

    objectif: Confidence | None = None
    origine: Confidence | None = None
    domaine: list[TagItem] = Field(default_factory=list, description="Value + confidence for each domaine chip")
    impact: list[TagItem] = Field(default_factory=list, description="Value + confidence for each impact chip")


class Constraints(BaseModel):
    """Typed downstream constraints derived from AI-generated tags."""

    domain: str = Field(description="Primary business domain (top domaine value)")
    impact: str = Field(description="Primary impact area (top impact value)")
    objective: str = Field(description="Primary objective classification (objectif value)")


class DuplicateMatch(BaseModel):
    """A potential duplicate business need found via vector similarity."""

    id: str
    pitch: str
    status: str
    similarity_score: float = Field(ge=0.0, le=1.0)


class RiskItem(BaseModel):
    """A single implementation or delivery risk (persisted JSON shape matches gap analysis)."""

    risk: str = Field(description="Description of the risk")
    severity: str = Field(description="Severity level: low | medium | high")


class Suggestion(BaseModel):
    """AI-generated pitch reformulation suggestion."""

    label: str = Field(description="Suggestion category label")
    text: str = Field(description="Suggested reformulation text")


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    """Request body for the /needs/analyze endpoint."""

    pitch: str = Field(min_length=1, description="Free-text pitch to analyze")
    horizon: Optional[Literal["court_terme", "moyen_terme", "long_terme"]] = Field(
        default=None,
        description="Planning horizon — guides objectif classification bias",
    )


class CreateNeedRequest(BaseModel):
    """Request body for POST /needs — only 2 fields from the user."""

    pitch: str = Field(min_length=20, description="Free-text pitch (≥20 chars)")
    horizon: Literal["court_terme", "moyen_terme", "long_terme"]
    tags: Tags | None = Field(default=None, description="Optional precomputed tags from /needs/analyze")

    @field_validator("pitch")
    @classmethod
    def pitch_not_blank(cls, v: str) -> str:
        """Ensure pitch is not just whitespace."""
        if not v.strip():
            raise ValueError("Pitch must not be empty or whitespace only")
        return v.strip()


class UpdateStatusRequest(BaseModel):
    """Request body for PATCH /needs/{id}/status."""

    status: Literal["submitted", "solutions_reviewed", "selected", "rework", "abandoned", "in_qualification", "delivery"]
    note: str | None = Field(default=None, description="Required when status=rework")

    @field_validator("note")
    @classmethod
    def note_required_for_rework_or_abandon(cls, v: str | None, info) -> str | None:
        """Validate that a note is provided when transitioning to rework or abandoned."""
        status = info.data.get("status")
        if status in ("rework", "abandoned") and not v:
            raise ValueError(f"A note/reason is required when setting status to '{status}'")
        return v


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class AnalyzeResponse(BaseModel):
    """Response for POST /needs/analyze."""

    tags: Tags = Field(description="Structured classifications with confidence on each facet")
    suggestions: list[Suggestion] = Field(default_factory=list)
    constraints: Constraints | None = Field(
        default=None,
        description="Derived primary objective / domain / impact for downstream use",
    )
    confidence: TagsConfidence | None = Field(
        default=None,
        description="Confidence snapshot keyed like tags — mirrors tag confidences without reserializing Tags",
    )


class BusinessNeedResponse(BaseModel):
    """Full business need object returned by the API."""

    id: str
    pitch: str
    horizon: Literal["court_terme", "moyen_terme", "long_terme"]
    tags: Tags
    confidence: dict | None = Field(
        default=None,
        description="Per-dimension AI confidence for tags (objectif, domaine, impact, origine)",
    )
    constraints: Constraints | None = None
    risks: list[RiskItem] = Field(default_factory=list, description="Latest gap-analysis risks")
    justifications: dict | None = Field(
        default=None,
        description="IVI and fit text rationales from latest gap analysis",
    )
    ivi_scores: dict | None = Field(
        default=None,
        description="IVI numeric scores (maturite, expertise, duree, impact) from latest gap analysis",
    )
    status: Literal["draft", "submitted", "solutions_reviewed", "selected", "rework", "abandoned", "in_qualification", "delivery"]
    rework_note: str | None = None
    duplicate_matches: list[DuplicateMatch] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Catalog search schemas
# ---------------------------------------------------------------------------

class CatalogProduct(BaseModel):
    """A DXC product returned by the catalog similarity search."""

    id: str
    name: str
    description: str

    # ── Excel-based fields (primary source of truth) ─────────────────────────
    domain: Optional[str] = None
    target_objective: Optional[str] = None
    maturity: Optional[str] = None          # poc | pilot | production
    client_sectors: list[str] = []
    complexity: Optional[str] = None        # low | medium | high
    ipm_stage: Optional[str] = None
    features: list[str] = []
    limitations: list[str] = []

    # ── Backwards-compatibility aliases (not populated from Excel) ────────────
    maturity_level: Optional[str] = None    # mirrors `maturity` for legacy clients
    internal_external: Optional[str] = None
    industry_focus: Optional[str] = None
    ai_type: Optional[str] = None
    ai_criticality: Optional[str] = None
    value_layer: Optional[str] = None
    monetization_potential: Optional[str] = None
    business_impact: Optional[str] = None
    lead: Optional[str] = None

    relevance_score: float


class CatalogSearchResponse(BaseModel):
    """Response for the catalog-search endpoint."""

    results: list[CatalogProduct]
    total: int


def _coerce_solution_features(value: object) -> list[str]:
    """Normalise heterogeneous ``features`` payloads (strings or small dicts) to labels."""
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        if isinstance(item, str):
            s = item.strip()
            if s:
                out.append(s)
        elif isinstance(item, dict) and item.get("name"):
            s = str(item["name"]).strip()
            if s:
                out.append(s)
    return out


# ---------------------------------------------------------------------------
# Gap analysis schemas — IVI model defined before GapAnalysisContext
# ---------------------------------------------------------------------------


class EvaluationScores(BaseModel):
    """IVI qualification scores derived from gap analysis, each with a one-sentence justification."""

    maturite: int = Field(
        ge=1,
        le=5,
        description="Solution maturity from catalog tier: PoC=2, Pilot=3, Production=4, Multi-ref=5",
    )
    maturite_justification: str = Field(default="", description="One-sentence rationale for maturite score")
    expertise: int = Field(ge=1, le=5, description="DXC expertise available to deliver (1=low, 5=high)")
    expertise_justification: str = Field(default="", description="One-sentence rationale for expertise score")
    duree: int = Field(ge=1, le=5, description="Delivery speed (5=fast, 1=long/complex)")
    duree_justification: str = Field(default="", description="One-sentence rationale for duree score")
    impact: int = Field(ge=1, le=5, description="Business impact on the identified need (1=low, 5=high)")
    impact_justification: str = Field(default="", description="One-sentence rationale for impact score")


class SelectedSolutionPayload(BaseModel):
    """Catalog solution snapshot for POST /needs/{need_id}/gap-analysis."""

    model_config = ConfigDict(extra="allow")

    id: str | None = Field(default=None, description="Catalog id e.g. EXCEL-12")
    name: str = Field(default="Unknown", description="Solution name")
    description: str = Field(default="", description="Solution description")
    features: list[str] = Field(default_factory=list)
    domain: str = Field(default="", description="Solution domain label from catalog")
    business_impact: str = ""
    maturity: str = Field(default="", description="Catalog maturity label")
    maturity_level: str = Field(default="", description="Legacy alias for maturity")
    complexity: str = Field(default="", description="low | medium | high when present")
    ipm_stage: str = ""
    relevance_score: float | None = Field(default=None, ge=0.0, le=1.0)

    @field_validator(
        "description",
        "domain",
        "business_impact",
        "maturity",
        "maturity_level",
        "complexity",
        "ipm_stage",
        mode="before",
    )
    @classmethod
    def _coerce_optional_string_fields(cls, v: object) -> str:
        """Echoed catalog JSON uses null for absent optional Excel fields."""
        if v is None:
            return ""
        return str(v)

    @field_validator("name", mode="before")
    @classmethod
    def _default_name_when_blank(cls, v: object) -> str:
        if v is None:
            return "Unknown"
        s = str(v).strip()
        return s if s else "Unknown"

    @field_validator("id", mode="before")
    @classmethod
    def _coerce_optional_id(cls, v: object) -> str | None:
        if v is None:
            return None
        s = str(v).strip()
        return s if s else None

    @field_validator("relevance_score", mode="before")
    @classmethod
    def _coerce_relevance_score(cls, v: object) -> float | None:
        """Accept 0–1 similarity or accidental 0–100 percentage payloads."""
        if v is None:
            return None
        try:
            x = float(v)
        except (TypeError, ValueError):
            return None
        if x > 1.0 and x <= 100.0:
            x = x / 100.0
        return min(1.0, max(0.0, x))

    @field_validator("features", mode="before")
    @classmethod
    def _features(cls, value: object) -> object:
        return _coerce_solution_features(value)


class GapAnalysisRequest(BaseModel):
    """Request body for POST /needs/{need_id}/gap-analysis."""

    selected_solution: SelectedSolutionPayload = Field(
        ...,
        description="Selected catalog solution — aligns with CatalogProduct fields.",
    )


class GapAnalysisContext(BaseModel):
    """Gap-analysis fields carried into POST /needs/{need_id}/recommendations."""

    model_config = ConfigDict(extra="allow")

    features_matching: list[str] = Field(default_factory=list)
    features_missing: list[str] = Field(default_factory=list)
    resources_needed: list[str] = Field(default_factory=list)
    risks: list[RiskItem] = Field(default_factory=list)
    fit_score: int = Field(default=5, ge=1, le=10)
    fit_justification: str = ""
    evaluation_scores: dict[str, Any] | EvaluationScores | None = None

    @field_validator("evaluation_scores", mode="before")
    @classmethod
    def _coerce_evaluation_scores(cls, v: object) -> object:
        if v is None or isinstance(v, dict):
            return v
        if isinstance(v, EvaluationScores):
            return v.model_dump()
        return v


class GapAnalysisResponse(BaseModel):
    """Response body for POST /needs/{need_id}/gap-analysis."""

    features_matching: list[str]
    features_missing: list[str]
    resources_needed: list[str]
    risks: list[RiskItem] = Field(default_factory=list, description="Implementation and delivery risks")
    fit_score: int = Field(ge=1, le=10)
    fit_justification: str = Field(default="", description="One-sentence rationale for fit_score")
    evaluation_scores: EvaluationScores
    solution_name: str


class RecommendationSolutionPayload(BaseModel):
    """One catalog row plus optional nested gap_analysis for POST /needs/{need_id}/recommendations."""

    model_config = ConfigDict(extra="allow")

    id: str = Field(default="", description="Catalog solution id")
    name: str = Field(default="", description="Solution display name")
    description: str = ""
    features: list[str] = Field(default_factory=list)
    domain: str = ""
    business_impact: str = ""
    maturity: str = ""
    maturity_level: str = ""
    complexity: str = ""
    relevance_score: float | None = Field(default=None, ge=0.0, le=1.0)
    gap_analysis: GapAnalysisContext | None = Field(
        default=None,
        description="Outputs from gap-analysis when the client persists them alongside the catalog row.",
    )
    evaluation_scores: dict[str, Any] | EvaluationScores | None = Field(
        default=None,
        description=(
            "IVI totals when inlined on the payload; otherwise taken from gap_analysis.evaluation_scores"
        ),
    )

    @field_validator(
        "id",
        "description",
        "domain",
        "business_impact",
        "maturity",
        "maturity_level",
        "complexity",
        mode="before",
    )
    @classmethod
    def _reco_null_str(cls, v: object) -> str:
        if v is None:
            return ""
        return str(v)

    @field_validator("name", mode="before")
    @classmethod
    def _reco_name(cls, v: object) -> str:
        if v is None:
            return ""
        return str(v)

    @field_validator("relevance_score", mode="before")
    @classmethod
    def _reco_rel(cls, v: object) -> float | None:
        if v is None:
            return None
        try:
            x = float(v)
        except (TypeError, ValueError):
            return None
        if x > 1.0 and x <= 100.0:
            x = x / 100.0
        return min(1.0, max(0.0, x))

    @field_validator("features", mode="before")
    @classmethod
    def _feat(cls, value: object) -> object:
        return _coerce_solution_features(value)

    @field_validator("evaluation_scores", mode="before")
    @classmethod
    def _eval_scores(cls, v: object) -> object:
        if v is None or isinstance(v, dict):
            return v
        if isinstance(v, EvaluationScores):
            return v.model_dump()
        return v


class RecommendationsRequest(BaseModel):
    """Request body for POST /needs/{need_id}/recommendations."""

    selected_solutions: list[RecommendationSolutionPayload] = Field(
        default_factory=list,
        description="Selections with optional gap_analysis for fit-aware recommendation mode.",
    )


# ---------------------------------------------------------------------------
# Delivery recommendations schemas (responses)
# ---------------------------------------------------------------------------


class RecommendationKPI(BaseModel):
    """A measurable KPI recommendation for a selected solution."""

    name: str
    target: str
    measurement_criteria: str


class OrganizationalRecommendation(BaseModel):
    """One organizational recommendation: accountable role plus concrete action."""

    role: str = Field(min_length=1, description="Role or profile accountable for the work")
    action: str = Field(min_length=1, description="Concrete organizational / delivery action")


class SolutionRecommendations(BaseModel):
    """Structured recommendations for one selected solution."""

    solution_id: str
    solution_name: str
    mode: Literal["STANDARD", "PREREQUIS"] = Field(
        default="STANDARD",
        description="PREREQUIS when gap fit_score ≤ 4 (1–10): outputs are prerequisites, not a delivery plan.",
    )
    technical_recommendations: list[str]
    organizational_recommendations: list[OrganizationalRecommendation]
    kpis: list[RecommendationKPI]


class RecommendationsResponse(BaseModel):
    """Response for the recommendations endpoint."""

    recommendations: list[SolutionRecommendations]


# ---------------------------------------------------------------------------
# Expertise team estimation (LLM + allow-list constraint)
# ---------------------------------------------------------------------------

class ExpertiseTeamRoleSlot(BaseModel):
    """One role required on the delivery team with FTE-equivalent headcount."""

    role: str = Field(min_length=1, description="Role label exactly from allowed_roles input")
    count: int = Field(ge=1, le=99, description="Number of individuals in this role")


class ExpertiseTeamEstimateRequest(BaseModel):
    """Estimate a constrained delivery roster from solution text."""

    solution_description: str = Field(min_length=1, description="Free-text solution scope / description")
    allowed_roles: list[str] = Field(
        default_factory=list,
        description="Permitted roles; if omitted or empty, the built-in default taxonomy is used",
    )

    @field_validator("solution_description")
    @classmethod
    def _strip_description(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("solution_description must not be empty")
        return s

    @field_validator("allowed_roles", mode="before")
    @classmethod
    def _coerce_roles(cls, v: object) -> object:
        if not isinstance(v, list):
            return v
        return [str(item).strip() for item in v if item is not None and str(item).strip()]


class ExpertiseTeamEstimateResponse(BaseModel):
    """Structured team estimate — roles are always a subset of the allow-list."""

    team: list[ExpertiseTeamRoleSlot]


# ---------------------------------------------------------------------------
# Duration formula engine (deterministic from gaps, team size, maturity)
# ---------------------------------------------------------------------------

class DurationEstimateRequest(BaseModel):
    """Inputs for calendar duration estimation."""

    features_missing: list[str] = Field(
        default_factory=list,
        description="Gap-analysis style capability gaps; count drives duration",
    )
    team_size: int = Field(
        ge=1,
        le=99,
        description="Total delivery headcount (e.g. sum of expertise-team counts)",
    )
    maturity: str = Field(
        min_length=1,
        description="Solution maturity label from catalog (same vocabulary as maturity scoring)",
    )

    @field_validator("maturity")
    @classmethod
    def _strip_maturity(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("maturity must not be empty")
        return s

    @field_validator("features_missing", mode="before")
    @classmethod
    def _coerce_features(cls, v: object) -> object:
        if not isinstance(v, list):
            return v
        out: list[str] = []
        for item in v:
            if item is None:
                continue
            t = str(item).strip()
            if t:
                out.append(t)
        return out


class DurationEstimateResponse(BaseModel):
    """Estimated elapsed time IVI-aligned speed score (5 = fast)."""

    duration_months: int = Field(ge=1, le=36, description="Rounded calendar months on the critical path")
    duration_score: int = Field(ge=1, le=5, description="Speed score aligned with IVI duree (5 = short)")


# ---------------------------------------------------------------------------
# Business impact scoring (rules + catalog-grounded LLM)
# ---------------------------------------------------------------------------

class CatalogImpactReference(BaseModel):
    """A narrative line tied to a single catalog row — facts must come from the catalog bundle only."""

    catalog_id: str = Field(min_length=1, description="Catalog id e.g. EXCEL-1")
    solution_name: str = Field(min_length=1)
    statement: str = Field(
        min_length=1,
        max_length=1200,
        description="Impact relevance phrased only from catalog fields provided to the model",
    )


class BusinessImpactScoreRequest(BaseModel):
    """Score how well a catalog solution aligns with business impact drivers."""

    pitch: str = Field(default="", description="Need pitch (optional context for the LLM)")
    domains: list[str] = Field(default_factory=list, description="Need domaine values")
    objective: str = Field(default="", description="Need objectif taxonomy value e.g. cost_reduction")
    impact: str = Field(default="", description="Primary impact label e.g. Cost, Revenue")
    selected_solution: dict = Field(description="Must include catalog id under key 'id' (EXCEL-…)")

    @model_validator(mode="after")
    def _require_catalog_id(self) -> BusinessImpactScoreRequest:
        raw = self.selected_solution
        if not isinstance(raw, dict):
            raise ValueError("selected_solution must be an object")
        sid = raw.get("id")
        if sid is None or not str(sid).strip():
            raise ValueError("selected_solution.id is required (catalog EXCEL-… id)")
        return self


class BusinessImpactScoreResponse(BaseModel):
    """Deterministic alignment plus optional catalog-only reference lines."""

    alignment_score: int = Field(ge=1, le=4, description="Rules-based need↔catalog impact alignment")
    references: list[CatalogImpactReference] = Field(
        default_factory=list,
        description="LLM-produced lines validated against supplied catalog ids only",
    )


class ExportDeliverySolution(BaseModel):
    """Selected solution summary included in export payload."""

    id: str
    name: str
    relevance: float
    overall: float


class ExportReportRequest(BaseModel):
    """Request body for document export endpoints."""

    recommendations: list[SolutionRecommendations]
    delivery_solutions: list[ExportDeliverySolution]
