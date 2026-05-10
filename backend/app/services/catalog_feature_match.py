"""Overlap between catalog solutions and business needs (Discovery catalogue filter).

Generic catalogue words such as ``model`` or ``learning`` must **not** count as overlap with an
otherwise unrelated need (they produced false positives like ROI Simulator ↔ recruiting pitches).
"""

from __future__ import annotations

import re
import unicodedata

CATALOG_FETCH_CAP = 40
CATALOG_RETURN_CAP = 5

_MIN_TOKEN_LEN = 3
_WORD_RE = re.compile(r"\w+", re.UNICODE)

_STOP = frozenset(
    """
    a an the and or but in on at to for of as is are was were be been being it its this that these those
    with from by not no yes all any some more most less than then so if we you our their will can may
    le la les un une des de du et ou en au aux pour par sur dans est son sa ses ce ces qui que dont où
    il elle nous vous ils elles être avoir faire tout toutefois aussi ainsi même très plus moins
    """.split()
)

_GLUE = frozenset(
    """
    driven based enabled scalable automated integrated actionable proactive seamless secure flexible
    comprehensive tailored customizable centralized holistic enterprise multi various multiple using
    within across ensures providing supports enables allows designed built real time self service
    """.split()
)

_IA_CATALOG_LEXICON = frozenset(
    {
        "nlp",
        "llm",
        "rag",
        "chatbot",
        "generative",
        "prediction",
        "predictive",
        "forecast",
        "forecasts",
        "inference",
        "transformer",
        "embeddings",
        "classification",
        "clustering",
        "explainable",
    }
)

_IA_PITCH_NEEDLES = (
    "machine learning",
    "deep learning",
    "nlp",
    "llm",
    "generative",
    "fine-tune",
    "neural",
)

_RECRUITING = frozenset(
    {
        "resume",
        "resumes",
        "cv",
        "cvs",
        "candidate",
        "candidates",
        "hiring",
        "recruit",
        "recruitment",
        "screening",
        "talent",
        "onboarding",
        "staffing",
    }
)

_RH_CATALOG_SURFACE = frozenset(
    {
        "hr",
        "talent",
        "workforce",
        "employee",
        "employees",
        "staffing",
        "onboarding",
        "recruitment",
        "recruiting",
        "candidate",
        "candidates",
        "resume",
        "conversational",
        "assistant",
    }
)

_CLOUD_LEXICON = frozenset({"azure", "aws", "saas", "kubernetes", "container", "serverless"})
_FINANCE_LEXICON = frozenset({"financial", "finance", "accounting", "treasury"})

_SHORT_ALLOWED = frozenset({"ai", "ml", "hr", "cv"})


def _fold(raw: str) -> str:
    s = unicodedata.normalize("NFKD", raw)
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def _tokens(text: str) -> set[str]:
    out: set[str] = set()
    for m in _WORD_RE.finditer(text):
        w = _fold(m.group(0))
        if len(w) < _MIN_TOKEN_LEN and w not in _SHORT_ALLOWED:
            continue
        if w in _STOP or w in _GLUE:
            continue
        out.add(w)
    return out


def _impact_split_tokens(labels: list[str]) -> set[str]:
    out: set[str] = set()
    for label in labels:
        if not isinstance(label, str) or not label.strip():
            continue
        parts = re.findall(r"[A-Za-z][a-z]+|[A-Za-z]+(?=[A-Z]|$)", label)
        for p in parts:
            w = _fold(p)
            if (
                len(w) >= _MIN_TOKEN_LEN or w in _SHORT_ALLOWED
            ) and w not in _STOP and w not in _GLUE:
                out.add(w)
    return out


def build_need_match_profile(
    *,
    pitch: str,
    objectif_str: str,
    domains_list: list[str],
    impact_parts: list[str],
) -> dict[str, object]:
    """Signals shared across all catalogue rows for one POST /catalog-search."""

    pitch_blob = " ".join(filter(None, [(pitch or "").strip(), (objectif_str or "").strip()]))
    pitch_folded = _fold(pitch_blob)
    pitch_lex = _tokens(pitch_blob)

    domain_slugs = {_fold(d) for d in domains_list if isinstance(d, str) and d.strip()}
    impact_lex = _impact_split_tokens(impact_parts)

    recruiting_pitch = bool(pitch_lex & _RECRUITING)
    ia_pitch = any(h in pitch_folded for h in _IA_PITCH_NEEDLES) or bool(
        pitch_lex & _IA_CATALOG_LEXICON
    )

    return {
        "pitch_folded": pitch_folded,
        "pitch_lex": pitch_lex,
        "domain_slugs": domain_slugs,
        "impact_lex": impact_lex,
        "recruiting_pitch": recruiting_pitch,
        "ia_pitch": ia_pitch,
    }


def _catalog_bundle_tokens(
    features: list[str],
    description: str,
    name: str,
) -> tuple[str, set[str]]:
    chunks: list[str] = []
    for f in features:
        if isinstance(f, str) and f.strip():
            chunks.append(f.strip())
    if isinstance(description, str) and description.strip():
        chunks.append(description.strip())
    if isinstance(name, str) and name.strip():
        chunks.append(name.strip())
    blob = "\n".join(chunks)
    folded = _fold(blob)
    return folded, _tokens(blob)


def _domain_tag_match(domain_slugs: set[str], cat_toks: set[str], cat_folded: str) -> bool:
    if "cloud" in domain_slugs and (cat_toks & _CLOUD_LEXICON):
        return True
    if "cybersecurite" in domain_slugs:
        if cat_toks & {"security", "cyber", "compliance"}:
            return True
        if "zero-trust" in cat_folded.replace(" ", ""):
            return True
        if "zero" in cat_toks and "trust" in cat_toks:
            return True
    if "finance" in domain_slugs and (cat_toks & _FINANCE_LEXICON):
        return True
    return False


def catalog_row_matches_need(
    features: list[str],
    description: str,
    name: str,
    *,
    profile: dict[str, object],
) -> bool:
    """True when catalogue bundle (features + description + title) aligns with the need."""

    cat_folded, cat_toks = _catalog_bundle_tokens(features, description, name)
    has_feature_line = bool([f for f in features if isinstance(f, str) and f.strip()])
    if not has_feature_line and not cat_folded.strip():
        return False

    pitch_lex: set[str] = profile["pitch_lex"]  # type: ignore[assignment]
    pitch_folded: str = profile["pitch_folded"]  # type: ignore[assignment]
    domain_slugs: set[str] = profile["domain_slugs"]  # type: ignore[assignment]
    impact_lex: set[str] = profile["impact_lex"]  # type: ignore[assignment]
    recruiting_pitch: bool = profile["recruiting_pitch"]  # type: ignore[assignment]
    ia_pitch: bool = profile["ia_pitch"]  # type: ignore[assignment]

    merged_need = pitch_lex | impact_lex

    direct = cat_toks & merged_need
    if direct:
        substantive_overlap = direct - {"ai", "ml"}
        if substantive_overlap:
            return True
        if direct & {"ai", "ml"} and ia_pitch:
            return True

    for tok in merged_need:
        if len(tok) >= _MIN_TOKEN_LEN and tok in cat_folded:
            return True

    if "rh" in domain_slugs:
        need_hr_proof = recruiting_pitch or bool(merged_need & _RECRUITING)
        if need_hr_proof:
            if cat_toks & _RH_CATALOG_SURFACE:
                return True
            if re.search(r"(?<![a-z0-9])hr(?![a-z0-9])", cat_folded):
                return True

    if (
        "ia" in domain_slugs
        and ia_pitch
        and (cat_toks & _IA_CATALOG_LEXICON)
    ):
        return True

    if _domain_tag_match(domain_slugs, cat_toks, cat_folded):
        return True

    return False
