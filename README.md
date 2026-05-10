# IPM — Innovation Progress Model

IPM is an AI-assisted innovation intake and qualification workspace. A user submits a business need, the platform classifies and enriches it with AI, searches the DXC catalog, scores candidate solutions, guides selection through stage gates, and produces delivery-ready recommendations and exportable documents.

The current implementation is a single-role experience for **CLIENT DXC**. There is no authentication or RBAC in this version.

---

## Product Flow

The workflow bar is sticky across the app and mirrors the operational path:

```
Sourcing → SG-1 → Discovery → SG-2 → Evaluation → Selection → SG-3 → Recos → SG-4 → Done
```

### Route Map

| Route | Step | What happens |
|---|---|---|
| `/sourcing` | Business Need | Capture pitch and horizon, classify with AI, validate SG-1 |
| `/discovery` | Discovery | Search DXC catalog, run gap analysis, validate SG-2 |
| `/evaluation` | Evaluation | Read selected discovery solutions and auto-score them from gap analysis |
| `/selection` | Selection | Choose solutions that move to delivery, validate SG-3 |
| `/recos` | Recos | Generate technical, organizational, and KPI recommendations, validate SG-4, export PDF/DOCX |
| `/dashboard` | Dashboard | View the current IPM list and status |

State is passed primarily through:
- `?id=` URL parameter for the current business need
- `localStorage` for selection and evaluation handoff data

Key localStorage keys:
- `ipm_selected_solutions` — selected solutions from Discovery
- `ipm_sg2_state` — SG-2 discovery validation state
- `ipm_evaluation_state` — ranked evaluation snapshot
- `ipm_delivery_solutions` — final delivery selections for Recos

---

## NLP Tagging Pipeline

The tagging pipeline runs every time a pitch is analyzed. It has three layers that run in sequence before the LLM is called, and two override layers that run after.

### Layer 1 — Confidence-Scored Tags

Every tag returned by the API carries a `confidence` level: `high`, `medium`, or `low`.

```json
{
  "tags": {
    "objectif": { "value": "cost_reduction", "confidence": "high" },
    "domaine":  [{ "value": "Finance", "confidence": "high" }, { "value": "IA", "confidence": "medium" }],
    "impact":   [{ "value": "Cost", "confidence": "high" }],
    "origine":  { "value": "probleme_operationnel", "confidence": "high" }
  }
}
```

The frontend renders an `H` / `M` / `L` badge on each tag chip. The left accent border color identifies the tag category.

### Layer 2 — Deterministic Rule Engine (Ticket 2.2)

`backend/app/services/rules_engine.py` runs **before** the LLM call and produces hard overrides:

| Rule | Trigger | Override |
|---|---|---|
| KPI detection | Numeric targets, %, ROI, SLA in the pitch | `origine = probleme_operationnel` (confidence: high) |
| Client reference | "client", "customer request", "contract requirement" | `origine = demande_client` — overrides KPI rule |
| IA vs Data | Data engineering keywords without any AI inference verbs | Removes `IA` from `domaine` |

Overrides are **injected into the LLM prompt** as explicit constraints and also **applied post-parse** to guarantee correctness regardless of LLM compliance. When Langfuse is configured, the NLP trace records the rule pipeline in trace metadata.

### Layer 3 — Horizon Injection

The planning horizon (`court_terme` / `moyen_terme` / `long_terme`) is passed to the LLM prompt as a `HORIZON CONTEXT` block that biases the `objectif` classification:

| Horizon | Bias |
|---|---|
| `court_terme` | Default to `cost_reduction` or `cx_improvement` — block `market_opportunity` unless explicitly stated |
| `moyen_terme` | Balanced — slight operational preference |
| `long_terme` | Default to `market_opportunity` or `risk_mitigation` — block pure quick-win objectives |

A **post-parse horizon override** enforces the bias when the LLM returns a contradictory `objectif` without hard pitch evidence (i.e. when the rule engine did not fire). Changing the horizon in the UI re-triggers analysis automatically.

### Tagging Pipeline Summary

```
pitch + horizon
  │
  ├─ [1] L1 cache check (in-memory, 5 min)
  ├─ [2] L2 cache check (Postgres, 24 h)  ← survives restarts
  ├─ [3] rules_engine.apply_rules()       ← deterministic, regex-based
  ├─ [4] _build_horizon_context()         ← horizon bias block
  ├─ [5] LLM call (rules_context + horizon_context injected)
  ├─ [6] _apply_rule_overrides()          ← hard post-parse rule enforcement
  ├─ [7] _apply_horizon_override()        ← horizon enforcement (skipped if rule engine fired)
  ├─ [8] sanitize_pitch_tag_dict()        ← enum / domaine / impact allow-lists before API models
  └─ [9] write L1 + L2 cache
```

---

## Post-LLM validation (allow-lists & bounds)

After the LLM (or when reading persisted JSON), the API applies a **validation layer** so responses stay on-vocabulary, bounded, and free of common disclaimer boilerplate:

| Output | Module | What gets enforced |
|---|---|---|
| NLP tags | `validation_guards.sanitize_pitch_tag_dict` | Permitted `objectif` / `origine` slugs; `domaine` → allow-list (unknown → `Autre`); `impact` → allow-list (unknown → `Cost`); confidence coercion |
| Organizational rows | `sanitize_organizational_recommendation`, `constrain_organizational_role` | Role titles mapped to a canonical list; action text length-capped |
| Gap `risks[]` | `sanitize_risk_fields` | Severity synonyms → `low` \| `medium` \| `high`; text scrub + max length |
| Solution `kpis[]` | `sanitize_recommendation_kpi_triplet` | KPI titles aligned to a small canonical catalogue when possible; scrub + length bounds on `target` and `measurement_criteria`; coherent defaults if a field is hollowed by scrubbing |

Hard prompts in `backend/app/core/llm_client.py` (`FALLBACK_PROMPTS`) and the Pydantic schemas should be treated as the **source of truth** for JSON field names and enums. The guards are a safety net when the model drifts.

---

## LLM Token Management

The analyze endpoint is called with a debounce and minimum pitch length to reduce unnecessary LLM calls:

- **Debounce:** 2000 ms (frontend waits 2 s after the user stops typing)
- **Min pitch length:** 30 characters (shorter inputs are not sent)
- **L2 Postgres cache:** analyzed pitches are cached for 24 hours and survive container restarts — repeated calls for the same pitch + horizon never reach the LLM

---

## Backend Services

| File | Purpose |
|---|---|
| `app/services/nlp_service.py` | LLM tagging pipeline orchestrator — cache, rules, horizon, overrides |
| `app/services/rules_engine.py` | Deterministic pre-LLM rule engine (KPI / client / IA-vs-Data) |
| `app/services/dxc_context.py` | Loads DXC capability context from Excel catalog (non-fatal if missing) |
| `app/services/catalog_loader.py` | Loads and normalises the DXC product catalog from Excel |
| `app/services/embedding_service.py` | Text embedding via local BGE model or OpenAI |
| `app/services/export_service.py` | PDF (ReportLab) and DOCX (python-docx) report generation |
| `app/services/id_service.py` | Year-scoped BN-YYYY-NNN ID generation |
| `app/services/validation_guards.py` | Post-LLM allow-lists for tags, org roles, risks, and KPIs |
| `app/core/llm_client.py` | LLM provider (Groq / Azure), Langfuse prompt fetch, fallback templates, intent-wrapped user messages |
| `app/core/intent_prompt.py` | Wraps every call’s user context in explicit / implicit / strategic intent blocks |
| `app/core/langfuse_tracking.py` | Attaches generations to parent traces (intent layers, variables, usage) |

---

## Database Models

| Table | Purpose |
|---|---|
| `business_needs` | Core business need records with JSONB tags |
| `id_counters` | Year-scoped counter for BN ID generation |
| `nlp_cache` | Persistent LLM tagging cache (24 h TTL, keyed by SHA-256 of pitch + horizon) |

Tables are created automatically at startup via `Base.metadata.create_all`.

---

## API Endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/v1/needs/analyze` | Classify a pitch — accepts optional `horizon` |
| `POST` | `/api/v1/needs` | Create a business need |
| `GET` | `/api/v1/needs` | List all needs (dashboard) |
| `GET` | `/api/v1/needs/{id}` | Get a single need |
| `PATCH` | `/api/v1/needs/{id}/status` | Advance workflow state |
| `POST` | `/api/v1/needs/{id}/catalog-search` | Search the DXC catalog |
| `POST` | `/api/v1/needs/{id}/gap-analysis` | Gap analysis for a selected solution |
| `POST` | `/api/v1/needs/{id}/recommendations` | Delivery recommendations per selected solution |
| `POST` | `/api/v1/needs/{id}/export/pdf` | Generate PDF report |
| `POST` | `/api/v1/needs/{id}/export/docx` | Generate DOCX proposal |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 App Router, React 18, TypeScript |
| Backend | FastAPI, SQLAlchemy async, Pydantic v2 |
| Database | PostgreSQL 15 |
| Vector DB | ChromaDB 0.5 |
| Embeddings | Local `BAAI/bge-small-en-v1.5` or OpenAI |
| LLM | Groq (`llama-3.3-70b-versatile`) or Azure OpenAI (GPT-4o) |
| Observability | Langfuse (hosted prompts + traces; repo fallbacks when offline or outdated `nlp_tagging`) |
| Export | ReportLab (PDF), python-docx (DOCX) |
| Storage | MinIO |
| Infra | Docker Compose |

---

## Run With Docker

```bash
docker compose up --build
```

Then open:
- Frontend: http://localhost:3000
- API docs: http://localhost:8000/docs
- MinIO UI: http://localhost:9001
- ChromaDB: http://localhost:8001

Hot-reloading is enabled for both backend and frontend in development — code changes take effect without rebuilding.

To stop the stack:

```bash
docker compose down
```

---

## Local Development

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## Environment Variables

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `CHROMA_HOST` | ChromaDB host |
| `CHROMA_PORT` | ChromaDB port |
| `MINIO_ENDPOINT` | MinIO endpoint |
| `MINIO_ACCESS_KEY` | MinIO access key |
| `MINIO_SECRET_KEY` | MinIO secret key |
| `LLM_PROVIDER` | `groq` or `azure` |
| `GROQ_API_KEY` | Groq API key |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI key |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint |
| `AZURE_OPENAI_DEPLOYMENT` | Azure deployment name (default: `gpt-4o`) |
| `AZURE_OPENAI_API_VERSION` | Azure API version |
| `EMBEDDING_PROVIDER` | `local` or `openai` |
| `OPENAI_API_KEY` | Required for OpenAI embeddings |
| `LANGFUSE_PUBLIC_KEY` | Langfuse public key |
| `LANGFUSE_SECRET_KEY` | Langfuse secret key |
| `LANGFUSE_HOST` | Langfuse host URL |
| `NEXT_PUBLIC_API_URL` | Frontend API base URL |

---

## Key Files

| Area | File |
|---|---|
| API routes | `backend/app/api/v1/needs.py` |
| LLM provider wrapper | `backend/app/core/llm_client.py` |
| NLP tagging pipeline | `backend/app/services/nlp_service.py` |
| Validation guards | `backend/app/services/validation_guards.py` |
| Langfuse helpers | `backend/app/core/langfuse_tracking.py` |
| Rule engine | `backend/app/services/rules_engine.py` |
| Pydantic schemas | `backend/app/schemas/business_need.py` |
| ORM models | `backend/app/models/business_need.py` |
| Runtime config | `backend/app/core/config.py` |
| Export generation | `backend/app/services/export_service.py` |
| Frontend API client | `frontend/src/lib/api.ts` |
| Frontend types | `frontend/src/lib/types.ts` |
| Analyze hook | `frontend/src/hooks/useAnalyze.ts` |
| Tag chips component | `frontend/src/components/sourcing/TagChips.tsx` |
| Sourcing shell | `frontend/src/components/sourcing/SourcingShell.tsx` |
| Workflow bar | `frontend/src/components/layout/WorkflowBar.tsx` |

---

## Langfuse Prompt Management

The backend fetches prompts from Langfuse by **prompt name** when keys are configured. If the client is unavailable, or (for `nlp_tagging` only) the hosted user template is missing mandatory fragments, the repo **falls back** to `FALLBACK_PROMPTS` in `backend/app/core/llm_client.py`.

### Prompt names in use

| Name | Used for |
|---|---|
| `nlp_tagging` | Pitch classification (`/needs/analyze`) — **validated** against required fragments (see below) |
| `gap-analysis` | Structured gap + IVI scores + risks (`/needs/{id}/gap-analysis`) |
| `solution-recommendations` | Technical, org, and KPI recommendations (`/needs/{id}/recommendations`) |
| `expertise-team-estimation` | Role mix for expertise display |
| `business-impact-references` | Catalogue-grounded reference blurbs for business impact scoring |

### Intent wrapping (all prompts)

After Langfuse `compile` (or fallback substitution), the **user** side of the prompt is wrapped via `build_intent_prompt`: callers pass `explicit`, `implicit`, and `strategic` string variables; those become `[EXPLICIT INTENT]`, `[IMPLICIT INTENT]`, and `[STRATEGIC INTENT - DXC POSITIONING]` sections, with the compiled user body under `[CONTEXT]`. Traces record both the pre-wrap context and the layered intent fields.

### `nlp_tagging` — required content in Langfuse

The hosted `nlp_tagging` **user** template must include these literals so it stays aligned with the tagging schema and rule injection:

- Words: `suggestions`, `confidence`
- Variable placeholders: `{{rules_context}}`, `{{horizon_context}}`

Example shape (placeholders may be reordered but must be present):

```
"""{{pitch}}"""

## PRE-DETERMINED RULES (enforce these — do not override)
{{rules_context}}

## HORIZON CONTEXT (use as classification bias — do not override explicit pitch signals)
{{horizon_context}}
```

For **`gap-analysis`**, **`solution-recommendations`**, and the other names, keep Langfuse copies in sync with the fallback text in `llm_client.py` (JSON shape, IVI field names `maturite` / `expertise` / `duree` / `impact`, and org/KPI rules). There is no automated drift check for those yet.

### Tracing

Gap analysis, solution recommendations, and NLP flows can open Langfuse **parent traces** and attach a **generation** per LLM call (`attach_llm_generation`), including rule pipeline metadata where implemented.

---

## Notes

- **Langfuse vs repo:** The implementation is consistent with the fallback prompts in the repository. If you use hosted prompts, update Langfuse when those fallbacks change — especially `nlp_tagging` fragments and JSON contracts for gap analysis and recommendations.
- The first Docker build takes several minutes — the backend downloads and warms the local embedding model (`BAAI/bge-small-en-v1.5`).
- If you change the DXC catalog Excel file, restart the API to re-seed ChromaDB and reload the capability context.
- The `nlp_cache` Postgres table persists analyzed pitches across restarts. To force a fresh analysis, delete the relevant row or wait for the 24 h TTL to expire.
- Groq free tier has a 100k token/day limit. The debounce and cache are tuned to stay within this for normal development usage.
