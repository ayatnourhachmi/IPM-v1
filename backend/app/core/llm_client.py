"""LLM abstraction — single interface for Groq and Azure OpenAI providers."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from app.core.config import settings
from app.core.intent_prompt import build_intent_prompt

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Langfuse prompt fallbacks (used when Langfuse is unreachable)
# ---------------------------------------------------------------------------

FALLBACK_PROMPTS: dict[str, dict[str, str]] = {
    "solution-recommendations": {
        "system": (
            "Produce delivery-ready recommendations for technical implementation,\n"
            "organization, and KPIs from the business need and selected solution "
            "in the user message.\n\n"
            "DXC ecosystem anchoring: ground every recommendation in recognizable "
            "enterprise technology and service practice. Primary anchor ecosystems — "
            "Microsoft (for example Azure, Microsoft 365, Power Platform, Dynamics), SAP, "
            "ServiceNow, AWS, and ITIL (service management, incident/change/release, "
            "continual improvement). Technical and organizational outputs must name "
            "concrete platforms, services, or ITIL-aligned processes where applicable; "
            "do not use vague generic phrasing (for example unspecified \"the cloud\", "
            "\"a platform\", or \"best practices\") without tying to one of the anchors "
            "above or to a clearly named successor in the same category.\n\n"
            "Return ONLY valid JSON — no markdown, no preamble, no explanation."
        ),
        "user": (
            "Business need:\n"
            "- Pitch: {{pitch}}\n"
            "- Objective: {{objectif}}\n"
            "- Expected impact: {{impact}}\n"
            "- Domains: {{domains}}\n\n"
            "Selected solution:\n"
            "- Name: {{solution_name}}\n"
            "- Description: {{solution_description}}\n"
            "- Features: {{solution_features}}\n"
            "- Business impact: {{solution_business_impact}}\n"
            "- Maturity: {{solution_maturity}}\n\n"
            "Gap and scoring context:\n"
            "- Matching features: {{features_matching}}\n"
            "- Missing features: {{features_missing}}\n"
            "- Resources needed: {{resources_needed}}\n"
            "- Fit score (1-10): {{fit_score}}\n"
            "- Fit justification: {{fit_justification}}\n"
            "- IVI scores (1-5): maturite={{eval_maturite}}, expertise={{eval_expertise}}, duree={{eval_duree}}, impact={{eval_impact}}\n"
            "- IVI justifications: maturite — {{eval_maturite_justification}} | expertise — {{eval_expertise_justification}} | duree — {{eval_duree_justification}} | impact — {{eval_impact_justification}}\n\n"
            "Recommendation mode: {{recommendation_mode}}\n"
            "{{mode_instructions}}\n"
            "Return this exact JSON structure:\n"
            "{\n"
            '  "technical_recommendations": ["..."],\n'
            '  "organizational_recommendations": [\n'
            '    { "role": "...", "action": "..." }\n'
            "  ],\n"
            '  "kpis": [\n'
            '    { "name": "...", "target": "...", "measurement_criteria": "..." }\n'
            "  ]\n"
            "}\n\n"
            "Rules:\n"
            "- Provide 4 to 6 technical recommendations (more if needed to satisfy the rule below).\n"
            "- Mandatory: For every distinct item listed under Missing features above, include at least one "
            "technical_recommendation whose wording explicitly references that gap (paraphrase is fine; omit none).\n"
            "- Technical recommendations must cover architecture, APIs/integrations, dependencies, data, and risks.\n"
            "- Provide 4 to 6 organizational recommendations (objects with \"role\" and \"action\"; more if needed "
            "for the rule below).\n"
            "- Mandatory: For every distinct item listed under Resources needed above, include at least one "
            "organizational_recommendation where \"action\" references that resource and \"role\" is the accountable "
            'profile (for example { "role": "Data Scientist", "action": '
            '"Build prediction models for churn scoring" }).\n'
            "- Organizational recommendations must otherwise cover workload, governance, and compliance themes.\n"
            "- Provide 3 to 5 KPIs with measurable target and measurement criteria.\n"
            "- KPIs should cite measurement via named stacks where sensible "
            '(for example ServiceNow reporting, SAP analytics, AWS or Azure monitoring), not abstract '
            "criteria alone.\n"
            "- When recommendation_mode above is PREREQUIS (fit weak: score ≤4 on a 1–10 scale): every "
            "recommendation and KPI must read as prerequisites, feasibility gates, and readiness proofs — "
            "not as a phased go-live or steady-state operations handover narrative.\n"
            "- Be concrete, implementation-oriented, and enterprise-ready.\n"
            "- Ecosystem anchoring: Across the full response, explicitly reference Microsoft, SAP, ServiceNow, "
            "AWS, and/or ITIL-grounded service management where relevant to the need; avoid purely generic suggestions."
        ),
    },
    "gap-analysis": {
        "system": (
            "Perform a structured gap analysis between a business need and a proposed DXC solution.\n"
            "Produce qualification scores across four IVI dimensions.\n"
            "Be specific and concise.\n"
            "Return ONLY valid JSON — no markdown, no explanation, no preamble."
        ),
        "user": (
            "Business need:\n\n"
            "Pitch: {{pitch}}\n"
            "Objective: {{objectif}}\n"
            "Expected impact: {{impact}}\n"
            "Domain: {{domains}}\n"
            "Downstream constraints: {{constraints}}\n\n"
            "Proposed DXC solution:\n\n"
            "Name: {{solution_name}}\n"
            "Description: {{solution_description}}\n"
            "Current features: {{solution_features}}\n"
            "Business impact: {{solution_business_impact}}\n"
            "Maturity: {{solution_maturity}}\n\n"
            "Return this exact JSON structure:\n"
            "{\n"
            '  "features_matching": ["feature that directly addresses the need", "..."],\n'
            '  "features_missing": ["capability the need requires but solution lacks", "..."],\n'
            '  "resources_needed": ["team / integration / data / infrastructure needed", "..."],\n'
            '  "risks": [\n'
            '    { "risk": "<specific implementation or delivery risk>", "severity": "low | medium | high" }\n'
            '  ],\n'
            '  "fit_score": <integer 1-10 where 10 = perfect fit>,\n'
            '  "fit_justification": "<one sentence explaining the fit_score>",\n'
            '  "evaluation_scores": {\n'
            '    "maturite": <integer 1-5 strictly from catalog solution maturity>,\n'
            '    "maturite_justification": "<one sentence>",\n'
            '    "expertise": <integer 1-5, DXC expertise available to deliver: 1=low, 5=high>,\n'
            '    "expertise_justification": "<one sentence>",\n'
            '    "duree": <integer 1-5, delivery speed: 5=fast/simple, 1=long/complex>,\n'
            '    "duree_justification": "<one sentence>",\n'
            '    "impact": <integer 1-5, business impact on the need: 1=marginal, 5=transformational>,\n'
            '    "impact_justification": "<one sentence>"\n'
            '  }\n'
            "}\n\n"
            "Rules:\n\n"
            "- features_matching: list only concrete overlaps, not generic claims.\n"
            "- features_missing: capabilities the solution structurally lacks — do NOT include risks here.\n"
            "- resources_needed: practical implementation requirements (people, infra, integrations).\n"
            "- risks: separate list for implementation/delivery risks (technical, organisational, timeline).\n"
            "  Each risk must have a severity of exactly 'low', 'medium', or 'high'.\n"
            "  Do NOT duplicate content between features_missing and risks.\n"
            "- fit_score: honest, calibrated, not optimistic by default.\n"
            "- fit_justification: one sentence summarising why the fit_score was assigned.\n"
            "- evaluation_scores.maturite: MUST match catalog maturity tier only "
            "(PoC=2, Pilot=3, Production=4, Multi-ref=5 — same numeric scale as ingestion engine).\n"
            "- evaluation_scores.expertise: reflect DXC's documented capabilities in the solution domain.\n"
            "- evaluation_scores.duree: 5 means deliverable quickly, 1 means long multi-quarter effort.\n"
            "- evaluation_scores.impact: how transformational is this solution for the stated business need.\n"
            "- Each *_justification must be a single sentence, max 20 words, grounded in the data above.\n"
            "- All score fields must be integers in their allowed ranges.\n"
            "- If uncertain, choose conservative scores and reflect uncertainty in missing/resources lists.\n"
            "- Return JSON only."
        ),
    },
    "expertise-team-estimation": {
        "system": (
            "You estimate delivery staffing for enterprise IT programmes.\n"
            "Choose roles only from the explicit list supplied by the user message.\n"
            "Never invent alternative job titles, abbreviations without a matching list entry, "
            "or synonyms not verbatim in that list.\n"
            "Return ONLY valid JSON — no markdown, no preamble, no explanation."
        ),
        "user": (
            "Solution description:\n{{solution_description}}\n\n"
            "Allowed roles (you MUST use these strings exactly for \"role\"; no others):\n"
            "{{allowed_roles_list}}\n\n"
            "Return ONLY this JSON object:\n"
            "{\n"
            '  "team": [\n'
            '    { "role": "<exact string from Allowed roles>", "count": <integer >= 1> }\n'
            "  ]\n"
            "}\n\n"
            "Rules:\n"
            "- Each \"role\" value must byte-match one line from Allowed roles "
            "(trim your choice to the canonical spelling shown).\n"
            "- Omit roles with count zero; omit duplicate lines for the same role "
            "(use one object with summed count if multiple needs apply).\n"
            "- Include only roles that are clearly needed for the solution description; "
            "typical output has 3–8 entries.\n"
            "- Counts are headcount / FTE estimates for a single coherent delivery wave.\n"
            "- Return JSON only."
        ),
    },
    "nlp_tagging": {
        "system": (
            "You are a senior innovation portfolio analyst at a large IT services company. "
            "Your job is to classify business need pitches into a structured taxonomy "
            "and score your confidence in each classification.\n\n"
            "## TAXONOMY DEFINITIONS\n\n"
            "### objectif (pick exactly ONE)\n"
            "- cost_reduction: The pitch focuses on reducing costs, eliminating waste, automating manual work, "
            "optimizing resources, or improving operational efficiency.\n"
            "- cx_improvement: The pitch focuses on improving customer experience, user satisfaction, "
            "service quality, communication channels, or employee experience.\n"
            "- risk_mitigation: The pitch focuses on reducing risk, improving security, ensuring compliance, "
            "disaster recovery, fraud detection, or regulatory adherence.\n"
            "- market_opportunity: The pitch focuses on capturing new markets, launching new products/services, "
            "generating new revenue streams, competitive advantage, or strategic positioning.\n\n"
            "### domaine (pick ONE or MORE from this exact list)\n"
            "- IA: Artificial intelligence, machine learning, NLP, computer vision, generative AI, chatbots, "
            "predictive models.\n"
            "- Cloud: Cloud migration, hybrid cloud, multi-cloud, SaaS, PaaS, IaaS, containerisation, "
            "serverless.\n"
            "- Cybersecurite: Security, zero-trust, SOC, SIEM, penetration testing, encryption, identity "
            "management, compliance (RGPD, ISO 27001).\n"
            "- Data: Data engineering, data lakes, data warehouses, BI, analytics, data governance, "
            "data quality, ETL/ELT pipelines.\n"
            "- RH: Human resources, recruitment, training, talent management, employee engagement, "
            "workforce planning, HRIS.\n"
            "- Finance: Accounting, financial reporting, budgeting, treasury, invoicing, payment processing, "
            "financial compliance.\n"
            "- Operations: Supply chain, logistics, manufacturing, procurement, facilities, project management, "
            "process automation (RPA), DevOps.\n"
            "- Autre: Anything that does not clearly fit the above categories.\n\n"
            "### impact (pick ONE or MORE from this exact list)\n"
            "- Revenue: Directly increases top-line revenue, monetisation, upsell, cross-sell.\n"
            "- Cost: Reduces operational costs, headcount, infrastructure spend, or manual effort.\n"
            "- Risk: Reduces exposure to security breaches, compliance fines, operational failures, or "
            "reputational damage.\n"
            "- CustomerExperience: Improves NPS, user satisfaction, response times, self-service, or "
            "client retention.\n\n"
            "### origine (pick exactly ONE)\n"
            "- enjeu_marche: Driven by market trends, competitive pressure, industry regulations, or "
            "emerging technologies.\n"
            "- probleme_operationnel: Driven by an internal pain point, inefficiency, recurring incident, "
            "or technical debt.\n"
            "- demande_client: Driven by explicit client feedback, feature request, contract requirement, "
            "or customer complaint.\n\n"
            "## CONFIDENCE SCORING\n"
            "Every classification must include a confidence level:\n"
            "- high: the pitch explicitly and unambiguously signals this classification\n"
            "- medium: the pitch implies this classification but is not fully explicit\n"
            "- low: the classification is inferred from weak, vague, or ambiguous signals\n\n"
            "For domaine and impact (multi-value fields), assign confidence PER ITEM independently.\n\n"
            "## RULES\n"
            "1. Respond ONLY with valid JSON. No explanation, no markdown fences, no commentary.\n"
            "2. Use ONLY the exact enum values listed above (case-sensitive).\n"
            "3. domaine and impact MUST be arrays with at least one element.\n"
            "4. objectif and origine MUST be single objects with 'value' and 'confidence' keys.\n"
            "5. Each item in domaine and impact MUST be an object with 'value' and 'confidence' keys.\n"
            "6. When the pitch is ambiguous, prefer the most specific classification over 'Autre'.\n"
            "7. When the pitch spans multiple objectives, pick the PRIMARY one.\n"
            "8. The pitch will typically be in French. Classify regardless of language."
        ),
        "user": (
            "Classify this business need pitch and suggest improvements:\n\n"
            '"""{{pitch}}"""\n\n'
            "## PRE-DETERMINED RULES (enforce these — do not override)\n"
            "{{rules_context}}\n\n"
            "## HORIZON CONTEXT (use as classification bias — do not override explicit pitch signals)\n"
            "{{horizon_context}}\n\n"
            "Return ONLY this JSON structure (no other text):\n"
            "{\n"
            '  "tags": {\n'
            '    "objectif": { "value": "cost_reduction | cx_improvement | risk_mitigation | market_opportunity", "confidence": "low | medium | high" },\n'
            '    "domaine":  [ { "value": "IA | Cloud | Cybersecurite | Data | RH | Finance | Operations | Autre", "confidence": "low | medium | high" } ],\n'
            '    "impact":   [ { "value": "Revenue | Cost | Risk | CustomerExperience", "confidence": "low | medium | high" } ],\n'
            '    "origine":  { "value": "enjeu_marche | probleme_operationnel | demande_client", "confidence": "low | medium | high" }\n'
            "  },\n"
            '  "suggestions": [\n'
            '    { "label": "Reformulation", "text": "<rewrite the pitch more clearly, 1 sentence max 20 words>" },\n'
            '    { "label": "Business Precision", "text": "<more specific version with measurable outcome, 1 sentence>" },\n'
            '    { "label": "Value Angle", "text": "<reframe around ROI or strategic value, 1 sentence>" }\n'
            "  ]\n"
            "}\n\n"
            "### EXAMPLES\n\n"
            'Pitch: "Automate monthly accounting reconciliations with an RPA tool to '
            'eliminate manual errors and reduce closing time from 5 days to 1 day."\n'
            "Answer:\n"
            "{\n"
            '  "tags": {\n'
            '    "objectif": { "value": "cost_reduction", "confidence": "high" },\n'
            '    "domaine":  [ { "value": "Finance", "confidence": "high" }, { "value": "IA", "confidence": "medium" } ],\n'
            '    "impact":   [ { "value": "Cost", "confidence": "high" }, { "value": "Risk", "confidence": "medium" } ],\n'
            '    "origine":  { "value": "probleme_operationnel", "confidence": "high" }\n'
            "  },\n"
            '  "suggestions": [\n'
            '    { "label": "Reformulation", "text": "Automate monthly accounting close via RPA to eliminate manual reconciliation errors." },\n'
            '    { "label": "Business Precision", "text": "Reduce reconciliation cycle from 5 to 1 day, targeting 99.5% entry accuracy." },\n'
            '    { "label": "Value Angle", "text": "Free up 80 hours/month of accounting work for higher-value activities." }\n'
            "  ]\n"
            "}\n\n"
            'Pitch: "We want to improve things internally."\n'
            "Answer:\n"
            "{\n"
            '  "tags": {\n'
            '    "objectif": { "value": "cost_reduction", "confidence": "low" },\n'
            '    "domaine":  [ { "value": "Operations", "confidence": "low" } ],\n'
            '    "impact":   [ { "value": "Cost", "confidence": "low" } ],\n'
            '    "origine":  { "value": "probleme_operationnel", "confidence": "low" }\n'
            "  },\n"
            '  "suggestions": [\n'
            '    { "label": "Reformulation", "text": "Specify what internal process needs improvement and the expected outcome." },\n'
            '    { "label": "Business Precision", "text": "Define a measurable target — e.g. reduce processing time by 30%." },\n'
            '    { "label": "Value Angle", "text": "Quantify the ROI: cost saved, hours freed, or error rate reduced." }\n'
            "  ]\n"
            "}\n\n"
            "Now classify the pitch above and generate 3 suggestions in English."
        ),
    },
    "business-impact-references": {
        "system": (
            "You summarise business-impact relevance **only** from the catalogue JSON embedded in "
            "the user message.\n"
            "Do not cite clients, sectors, deployments, maturity, objectives, outcomes, KPIs or "
            "features that are absent from that JSON.\n"
            "Do not invent quotations, percentages, timelines, geography, regulators, analysts, "
            "or unnamed case studies.\n"
            "The alignment_score is already computed — treat it as read-only contextual metadata.\n"
            "Return ONLY valid JSON — no markdown, preamble, or commentary."
        ),
        "user": (
            "Deterministic alignment score (already fixed — do NOT change): {{alignment_score}} on scale 1–4.\n\n"
            "Need context (hint only — all factual claims MUST still trace to catalogue JSON):\n"
            "- Pitch: {{need_pitch}}\n"
            "- Domains: {{need_domains}}\n"
            "- Objective tag: {{need_objective}}\n"
            "- Impact tag: {{need_impact}}\n\n"
            "Catalogue records (sole source of truth — no other knowledge):\n"
            "{{catalog_cases_json}}\n\n"
            "Return ONLY this JSON object:\n"
            "{\n"
            '  "references": [\n'
            "    {\n"
            '      "catalog_id": "<must match a catalog_id from the JSON above>",\n'
            '      "solution_name": "<exact solution_name from the same record>",\n'
            '      "statement": "<1–2 sentences tying that record to the need using only fields from that record>"\n'
            "    }\n"
            "  ]\n"
            "}\n\n"
            "Rules:\n"
            "- Include 1–3 references; prefer the primary record (first in the JSON) when it is relevant.\n"
            "- Each statement must paraphrase explicit catalogue fields (deployments, client_sectors, "
            "target_objective, features, limitations, domain, maturity, description).\n"
            "- If a field is empty in the JSON, do not mention it.\n"
            "- Never output references for catalog_ids not present in the JSON.\n"
            "- Return JSON only."
        ),
    },
}


@dataclass(frozen=True)
class BuiltPrompt:
    """Rendered prompts + intent decomposition (Langfuse observability)."""

    system_prompt: str
    user_prompt: str
    context_before_intent: str
    intent_explicit: str
    intent_implicit: str
    intent_strategic: str


@dataclass
class LLMResponse:
    """Structured response from the LLM provider."""

    content: str
    usage: dict[str, int]


def _build_prompt(prompt_name: str, variables: dict[str, str]) -> BuiltPrompt:
    """Fetch a prompt from Langfuse, fall back locally, compile variables + intent wrapping."""
    try:
        from langfuse import Langfuse

        lf = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
        prompt = lf.get_prompt(prompt_name)

        if prompt_name == "nlp_tagging" and prompt_name in FALLBACK_PROMPTS:
            raw = prompt.prompt  # str for text prompts, list[dict] for chat prompts
            if isinstance(raw, list):
                raw_user = next((m["content"] for m in raw if m["role"] == "user"), "")
            else:
                raw_user = str(raw)
            required_literals = ("suggestions", "confidence")
            required_vars = ("{{rules_context}}", "{{horizon_context}}")
            missing = [kw for kw in (*required_literals, *required_vars) if kw not in raw_user]
            if missing:
                logger.warning(
                    "Langfuse prompt '%s' is outdated (missing: %s), using fallback",
                    prompt_name,
                    missing,
                )
                raise ValueError("outdated prompt")

        compiled = prompt.compile(**variables)
        if isinstance(compiled, list):
            system_msg = next((m["content"] for m in compiled if m["role"] == "system"), "")
            user_msg = next((m["content"] for m in compiled if m["role"] == "user"), "")
        else:
            system_msg, user_msg = "", str(compiled)

        explicit = variables.get("explicit", "")
        implicit = variables.get("implicit", "")
        strategic = variables.get("strategic", "")
        context = user_msg
        user_wrapped = build_intent_prompt(explicit, implicit, strategic, context)
        return BuiltPrompt(
            system_prompt=system_msg,
            user_prompt=user_wrapped,
            context_before_intent=context,
            intent_explicit=str(explicit),
            intent_implicit=str(implicit),
            intent_strategic=str(strategic),
        )
    except Exception as exc:
        logger.warning("Langfuse unavailable (%s), using fallback prompt for '%s'", exc, prompt_name)
        fallback = FALLBACK_PROMPTS.get(prompt_name)
        if not fallback:
            raise ValueError(f"No fallback prompt defined for '{prompt_name}'") from exc
        system_text = fallback["system"]
        user_text = fallback["user"]
        for key, value in variables.items():
            user_text = user_text.replace("{{" + key + "}}", value)
            system_text = system_text.replace("{{" + key + "}}", value)
        explicit = variables.get("explicit", "")
        implicit = variables.get("implicit", "")
        strategic = variables.get("strategic", "")
        context = user_text
        user_wrapped = build_intent_prompt(explicit, implicit, strategic, context)
        return BuiltPrompt(
            system_prompt=system_text,
            user_prompt=user_wrapped,
            context_before_intent=context,
            intent_explicit=str(explicit),
            intent_implicit=str(implicit),
            intent_strategic=str(strategic),
        )


async def _complete_groq(system_prompt: str, user_prompt: str, response_format: str | None) -> LLMResponse:
    """Call Groq API with llama-3.3-70b-versatile."""
    from groq import AsyncGroq

    client = AsyncGroq(api_key=settings.groq_api_key)
    kwargs: dict = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.1,
        "max_tokens": 1024,
    }
    if response_format == "json":
        kwargs["response_format"] = {"type": "json_object"}

    response = await client.chat.completions.create(**kwargs)
    choice = response.choices[0]
    return LLMResponse(
        content=choice.message.content or "",
        usage={
            "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
            "completion_tokens": response.usage.completion_tokens if response.usage else 0,
        },
    )


async def _complete_azure(system_prompt: str, user_prompt: str, response_format: str | None) -> LLMResponse:
    """Call Azure OpenAI with GPT-4o."""
    from openai import AsyncAzureOpenAI

    client = AsyncAzureOpenAI(
        api_key=settings.azure_openai_api_key,
        azure_endpoint=settings.azure_openai_endpoint,
        api_version=settings.azure_openai_api_version,
    )
    kwargs: dict = {
        "model": settings.azure_openai_deployment,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.1,
        "max_tokens": 1024,
    }
    if response_format == "json":
        kwargs["response_format"] = {"type": "json_object"}

    response = await client.chat.completions.create(**kwargs)
    choice = response.choices[0]
    return LLMResponse(
        content=choice.message.content or "",
        usage={
            "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
            "completion_tokens": response.usage.completion_tokens if response.usage else 0,
        },
    )


async def complete(
    prompt_name: str,
    variables: dict[str, str],
    response_format: str | None = None,
    *,
    lf_parent_trace: object | None = None,
) -> LLMResponse:
    """Unified LLM completion — dispatches to configured provider; optional Langfuse trace."""
    built = _build_prompt(prompt_name, variables)

    if settings.llm_provider == "groq":
        response = await _complete_groq(built.system_prompt, built.user_prompt, response_format)
        model_label = "llama-3.3-70b-versatile"
    elif settings.llm_provider == "azure":
        response = await _complete_azure(built.system_prompt, built.user_prompt, response_format)
        model_label = settings.azure_openai_deployment or "azure-openai"
    else:
        raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")

    if lf_parent_trace is not None:
        from app.core.langfuse_tracking import attach_llm_generation

        attach_llm_generation(
            lf_parent_trace,
            prompt_name=prompt_name,
            model_label=model_label,
            system_prompt=built.system_prompt,
            user_prompt=built.user_prompt,
            intent_explicit=built.intent_explicit,
            intent_implicit=built.intent_implicit,
            intent_strategic=built.intent_strategic,
            context_before_intent=built.context_before_intent,
            variable_snapshot=variables,
            completion_text=response.content,
            usage=response.usage,
        )
    return response


def parse_json_response(response: LLMResponse) -> dict:
    """Parse a JSON response from the LLM, stripping markdown fences if present."""
    content = response.content.strip()
    if content.startswith("```"):
        lines = content.split("\n")
        content = "\n".join(lines[1:-1])
    return json.loads(content)
