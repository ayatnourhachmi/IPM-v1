"""Post-LLM validation: canonical tag mappings, org-role allow-list, KPI/risk guards, bounded text."""

from __future__ import annotations

import logging
import unicodedata
from typing import Any

logger = logging.getLogger(__name__)

# --- NLP tagging (aligned with FALLBACK_PROMPTS / Tags Literals in schemas) ---
ALLOWED_OBJECTIF: frozenset[str] = frozenset(
    {"cost_reduction", "cx_improvement", "risk_mitigation", "market_opportunity"}
)
ALLOWED_ORIGINE: frozenset[str] = frozenset(
    {"enjeu_marche", "probleme_operationnel", "demande_client"}
)

# Allowed domain labels (prompt + UI); unknown → Autre
ALLOWED_DOMAINE: frozenset[str] = frozenset(
    {"IA", "Cloud", "Cybersecurite", "Data", "RH", "Finance", "Operations", "Autre"}
)

# Allowed impact labels (prompt); unknown → Cost (safe default)
ALLOWED_IMPACT: frozenset[str] = frozenset(
    {"Revenue", "Cost", "Risk", "CustomerExperience"}
)

_DEFAULT_OBJECTIF = "cost_reduction"
_DEFAULT_ORIGINE = "probleme_operationnel"

# Normalized-key → canonical slug (objectif / origine)
_OBJECTIF_ALIASES: dict[str, str] = {
    "cost_reduction": "cost_reduction",
    "cost": "cost_reduction",
    "cx_improvement": "cx_improvement",
    "customer_experience": "cx_improvement",
    "cx": "cx_improvement",
    "risk_mitigation": "risk_mitigation",
    "risk": "risk_mitigation",
    "market_opportunity": "market_opportunity",
    "market": "market_opportunity",
    "growth": "market_opportunity",
}

_ORIGINE_ALIASES: dict[str, str] = {
    "enjeu_marche": "enjeu_marche",
    "probleme_operationnel": "probleme_operationnel",
    "demande_client": "demande_client",
    "market": "enjeu_marche",
    "client": "demande_client",
    "customer": "demande_client",
    "operational": "probleme_operationnel",
    "operations": "probleme_operationnel",
}

# Normalized display key → canonical domaine label (exact casing for API)
_DOMAINE_ALIASES: dict[str, str] = {
    "ia": "IA",
    "ai": "IA",
    "intelligence artificielle": "IA",
    "cloud": "Cloud",
    "cybersecurite": "Cybersecurite",
    "cybersecurity": "Cybersecurite",
    "cyber": "Cybersecurite",
    "security": "Cybersecurite",
    "data": "Data",
    "rh": "RH",
    "hr": "RH",
    "human resources": "RH",
    "finance": "Finance",
    "operations": "Operations",
    "operation": "Operations",
    "autre": "Autre",
    "other": "Autre",
}

_IMPACT_ALIASES: dict[str, str] = {
    "revenue": "Revenue",
    "cost": "Cost",
    "risk": "Risk",
    "customerexperience": "CustomerExperience",
    "customer_experience": "CustomerExperience",
    "cx": "CustomerExperience",
    "satisfaction": "CustomerExperience",
}

# --- Organizational recommendations (LLM + synthetic rows) ---
CANONICAL_ORGANIZATIONAL_ROLES: tuple[str, ...] = (
    "Program / delivery leadership",
    "Resource management",
    "Governance",
    "Change adoption",
    "Security / risk",
    "Executive steering / portfolio",
    "Solution / product sponsorship",
    "Architecture and integration SMEs",
    "Resource / workforce planning",
    "Implementation partner",
    "Implementation lead",
    "Data Scientist",
    "Data Engineer",
    "Integration Engineer",
    "Security / Compliance Analyst",
    "Platform / Infrastructure Engineer",
    "Frontend Engineer",
    "Backend Engineer",
    "Business Analyst",
)

_DEFAULT_ORG_ROLE = "Program / delivery leadership"
_MAX_ORG_ACTION_LEN = 4000


def _norm_token(s: str) -> str:
    return " ".join(s.strip().lower().split())


def _fold(s: str) -> str:
    """Lowercase + strip accents for fuzzy compares."""
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def _coerce_confidence(conf: Any) -> str:
    raw = str(conf or "low").lower().strip()
    if raw not in ("low", "medium", "high"):
        return "low"
    return raw


def _sanitize_scalar_tag(
    blob: dict[str, Any],
    *,
    aliases: dict[str, str],
    allowed: frozenset[str],
    default: str,
    field_name: str,
) -> dict[str, Any]:
    blob_copy = dict(blob)
    raw_val = blob_copy.get("value", default)
    val = str(raw_val).strip() if raw_val is not None else default
    conf = _coerce_confidence(blob_copy.get("confidence"))

    if val in allowed:
        out_val = val
    else:
        nk2 = _norm_token(val.replace("_", " ")).replace(" ", "_")
        nk3 = _norm_token(val)
        mapped = (
            aliases.get(nk2)
            or aliases.get(nk3.replace(" ", "_"))
            or aliases.get(_fold(val))
        )
        if mapped in allowed:
            out_val = mapped
        else:
            logger.info(
                "Tag guard: unknown %s value %r — using default %r",
                field_name,
                val,
                default,
            )
            out_val = default
            if conf == "high":
                conf = "medium"

    blob_copy["value"] = out_val
    blob_copy["confidence"] = conf
    return blob_copy


def _sanitize_domaine_item(item: dict[str, Any]) -> dict[str, Any]:
    raw = item.get("value", "Autre")
    val = str(raw).strip() if raw is not None else "Autre"
    if val in ALLOWED_DOMAINE:
        canon = val
    else:
        nk = _fold(val)
        mapped = _DOMAINE_ALIASES.get(nk)
        # Try without folding spaces
        if mapped is None:
            mapped = _DOMAINE_ALIASES.get(_norm_token(val).replace(" ", ""))
        if mapped in ALLOWED_DOMAINE:
            canon = mapped
        else:
            logger.info(
                "Tag guard: unknown domaine value %r — remapping to Autre",
                val,
            )
            canon = "Autre"
            item = dict(item)
            item["confidence"] = "low"
    return {"value": canon, "confidence": _coerce_confidence(item.get("confidence"))}


def _sanitize_impact_item(item: dict[str, Any]) -> dict[str, Any]:
    raw = item.get("value", "Cost")
    val = str(raw).strip() if raw is not None else "Cost"
    if val in ALLOWED_IMPACT:
        canon = val
    else:
        nk = _fold(val.replace(" ", ""))
        mapped = _IMPACT_ALIASES.get(nk)
        if mapped is None:
            nk2 = _norm_token(val).replace(" ", "")
            mapped = _IMPACT_ALIASES.get(nk2)
        if mapped in ALLOWED_IMPACT:
            canon = mapped
        else:
            logger.info(
                "Tag guard: unknown impact value %r — remapping to Cost",
                val,
            )
            canon = "Cost"
            item = dict(item)
            item["confidence"] = "low"
    return {"value": canon, "confidence": _coerce_confidence(item.get("confidence"))}


def sanitize_pitch_tag_dict(tag_dict: dict[str, Any]) -> dict[str, Any]:
    """Ensure tag dict satisfies Tags Literals/lists before constructing ``Tags``.

    Drops unknown enums, fixes common aliases, maps unknown domaine→Autre / impact→Cost.
    """
    out = dict(tag_dict)
    obj = out.get("objectif")
    if isinstance(obj, dict):
        out["objectif"] = _sanitize_scalar_tag(
            obj,
            aliases=_OBJECTIF_ALIASES,
            allowed=ALLOWED_OBJECTIF,
            default=_DEFAULT_OBJECTIF,
            field_name="objectif",
        )
    ori = out.get("origine")
    if isinstance(ori, dict):
        out["origine"] = _sanitize_scalar_tag(
            ori,
            aliases=_ORIGINE_ALIASES,
            allowed=ALLOWED_ORIGINE,
            default=_DEFAULT_ORIGINE,
            field_name="origine",
        )

    domaine_raw = out.get("domaine")
    dom_out: list[dict[str, Any]] = []
    if isinstance(domaine_raw, list):
        for x in domaine_raw:
            if isinstance(x, dict):
                dom_out.append(_sanitize_domaine_item(x))
            elif isinstance(x, str) and x.strip():
                dom_out.append(_sanitize_domaine_item({"value": x.strip(), "confidence": "low"}))
    out["domaine"] = dom_out if dom_out else [{"value": "Autre", "confidence": "low"}]

    impact_raw = out.get("impact")
    imp_out: list[dict[str, Any]] = []
    if isinstance(impact_raw, list):
        for x in impact_raw:
            if isinstance(x, dict):
                imp_out.append(_sanitize_impact_item(x))
            elif isinstance(x, str) and x.strip():
                imp_out.append(_sanitize_impact_item({"value": x.strip(), "confidence": "low"}))
    out["impact"] = imp_out if imp_out else [{"value": "Cost", "confidence": "low"}]

    return out


def _build_org_role_lookup() -> dict[str, str]:
    m: dict[str, str] = {}
    for r in CANONICAL_ORGANIZATIONAL_ROLES:
        m[_norm_token(r)] = r
        m[_norm_token(r.replace("/", " "))] = r
        m[r.lower()] = r
    return m


_ORG_ROLE_LOOKUP = _build_org_role_lookup()


def constrain_organizational_role(role: str) -> str:
    """Map free-text role to the nearest canonical label; never return an unknown title."""
    stripped = str(role or "").strip()
    if not stripped:
        return _DEFAULT_ORG_ROLE
    key = _norm_token(stripped)
    if key in _ORG_ROLE_LOOKUP:
        return _ORG_ROLE_LOOKUP[key]
    lk = stripped.lower()
    if lk in _ORG_ROLE_LOOKUP:
        return _ORG_ROLE_LOOKUP[lk]
    low = stripped.lower()
    for canon in CANONICAL_ORGANIZATIONAL_ROLES:
        cl = canon.lower()
        if cl == low or cl in low or low in cl:
            return canon
    logger.info(
        "Org role guard: unknown role %r — using %r",
        stripped,
        _DEFAULT_ORG_ROLE,
    )
    return _DEFAULT_ORG_ROLE


def clamp_org_action_text(action: str) -> str:
    """Bound action length so pathological completions cannot overwhelm responses."""
    a = " ".join(str(action or "").strip().split())
    if len(a) <= _MAX_ORG_ACTION_LEN:
        return a
    return a[: _MAX_ORG_ACTION_LEN - 1].rstrip() + "…"


def sanitize_organizational_recommendation(role: str, action: str) -> tuple[str, str]:
    return constrain_organizational_role(role), clamp_org_action_text(action)


# --- Gap risks & delivery KPIs (LLM + persisted JSON) ---
_MAX_RISK_TEXT_LEN = 2500
_MAX_KPI_NAME_LEN = 160
_MAX_KPI_TARGET_LEN = 2500
_MAX_KPI_CRITERIA_LEN = 2500

_LLM_BOILERPLATE_SUBSTRINGS: tuple[str, ...] = (
    "as a language model",
    "as an ai language model",
    "as an ai",
    "i cannot provide",
    "i can't provide",
    "i'm an ai",
    "i am an ai",
    "chatgpt",
    "openai",
)

# Canonical KPI names (align with hardcoded fallbacks in needs.py recommendations).
_CANONICAL_KPI_NAMES: tuple[str, ...] = (
    "Time-to-value",
    "Adoption rate",
    "Operational impact",
    "Prerequisite register completeness",
    "Executive go/no-go prereq checkpoint",
    "Integration unknowns retired",
)

_DEFAULT_KPI_NAME_BY_MODE: dict[str, str] = {
    "PREREQUIS": "Prerequisite readiness KPI",
    "STANDARD": "Operational outcome KPI",
}


def _clamp_text(text: str, max_len: int) -> str:
    t = " ".join(str(text or "").strip().split())
    if len(t) <= max_len:
        return t
    return t[: max_len - 1].rstrip() + "…"


def scrub_free_text(text: str) -> str:
    """Remove common LLM disclaimer phrases (case-insensitive) and collapse whitespace."""
    t = str(text or "")
    lower = t.lower()
    for bad in _LLM_BOILERPLATE_SUBSTRINGS:
        while bad in lower:
            i = lower.index(bad)
            t = t[:i] + " " + t[i + len(bad) :]
            lower = t.lower()
    return " ".join(t.split())


def constrain_risk_severity(severity: str) -> str:
    """Normalize severity to gap-analysis contract: low | medium | high."""
    s = str(severity or "").lower().strip()
    aliases_high = frozenset(
        {"high", "critical", "severe", "major", "urgent", "p1", "s1"}
    )
    aliases_low = frozenset({"low", "minor", "trivial", "negligible", "p4", "s4"})
    aliases_med = frozenset({"medium", "med", "moderate", "mod", "p2", "p3", "s2", "s3"})
    if s in aliases_high:
        return "high"
    if s in aliases_low:
        return "low"
    if s in aliases_med or s == "mid":
        return "medium"
    return "medium"


def sanitize_risk_fields(risk_text: str, severity: str) -> tuple[str, str]:
    """Scrub boilerplate, bound length, coerce severity."""
    scrubbed = scrub_free_text(risk_text)
    if not scrubbed.strip():
        scrubbed = "Implementation or delivery risk (detail to refine with steering)."
    return _clamp_text(scrubbed, _MAX_RISK_TEXT_LEN), constrain_risk_severity(severity)


def _build_kpi_name_lookup() -> dict[str, str]:
    m: dict[str, str] = {}
    for canon in _CANONICAL_KPI_NAMES:
        variants = (
            canon,
            canon.replace("-", " "),
            _norm_token(canon),
            _norm_token(canon.replace("-", "")),
            _fold(canon),
        )
        for v in variants:
            if v:
                m[v] = canon
        m.setdefault(_fold(canon.replace("-", " ").replace("/", " ")), canon)
    return m


_KPI_LOOKUP = _build_kpi_name_lookup()

_KPI_SYNONYMS: dict[str, str] = {
    "time to value": "Time-to-value",
    "time-to-value": "Time-to-value",
    "adoption rate": "Adoption rate",
    "user adoption": "Adoption rate",
    "operational impact": "Operational impact",
    "prerequisite register completeness": "Prerequisite register completeness",
    "integration unknowns": "Integration unknowns retired",
    "go/no-go prereq checkpoint": "Executive go/no-go prereq checkpoint",
    "exec go/no-go": "Executive go/no-go prereq checkpoint",
}


def constrain_kpi_name(name: str, *, mode: str = "STANDARD") -> str:
    """Map LLM KPI titles to canonical names when possible; else clamp preserving intent."""
    default = _DEFAULT_KPI_NAME_BY_MODE.get(mode.upper(), _DEFAULT_KPI_NAME_BY_MODE["STANDARD"])
    cleaned = scrub_free_text(name)
    if not cleaned:
        return default

    nk = _norm_token(cleaned)
    if nk in _KPI_SYNONYMS:
        return _KPI_SYNONYMS[nk]
    fk = _fold(cleaned)
    if fk in _KPI_LOOKUP:
        return _KPI_LOOKUP[fk]
    # Normalized substring match vs canonical catalogue (prefer longer canon first)
    for canon in sorted(_CANONICAL_KPI_NAMES, key=len, reverse=True):
        cn = _norm_token(canon.replace("-", " "))
        if len(cn) < 8:
            continue
        if cn in nk or nk in cn:
            return canon

    return _clamp_text(cleaned, _MAX_KPI_NAME_LEN)


def sanitize_recommendation_kpi_triplet(
    name: str,
    target: str,
    measurement_criteria: str,
    *,
    mode: str = "STANDARD",
) -> tuple[str, str, str]:
    """Normalize KPI naming, strip LLM fluff, constrain field lengths."""
    canon_name = constrain_kpi_name(name, mode=mode)
    target_s = _clamp_text(scrub_free_text(target), _MAX_KPI_TARGET_LEN)
    criteria_s = _clamp_text(scrub_free_text(measurement_criteria), _MAX_KPI_CRITERIA_LEN)
    # If scrub hollowed strings, keep KPI row coherent
    if not target_s.strip():
        target_s = (
            "Quantified outcome documented in steering or operational reviews within the horizon."
            if mode.upper() == "STANDARD"
            else "Tracked evidence in prerequisites register reviewed in governance cadence."
        )
    if not criteria_s.strip():
        criteria_s = (
            "Verifiable artefact per enterprise PMO / ITSM tooling (baseline vs actual)."
            if mode.upper() == "STANDARD"
            else "Formal review record tying metric to prerequisite exit criteria."
        )
    return canon_name, target_s, criteria_s
