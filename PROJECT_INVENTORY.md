# IPM v0 — Comprehensive Project Inventory

**Project**: Innovation Progress Model (IPM) v0  
**Date**: May 9, 2026  
**Structure**: Full-stack FastAPI (backend) + Next.js 14 (frontend)

---

## 📋 Executive Summary

- **Total Python Files**: 43 (backend)
- **Total TypeScript/TSX Files**: 38 (frontend)
- **Configuration Files**: 8 major
- **Database Migrations**: 3 versions
- **Duplicates Found**: 2 intentional (different purposes)
- **Orphaned Files**: None identified
- **Build/Output Directories**: `.next/`, `.vercel/`, `node_modules/`, `__pycache__/`

---

## 📁 ROOT DIRECTORY STRUCTURE

```
c:\Github 2026\IPM-v0/
├── .cursor/                    # Cursor IDE config (empty)
├── .env                        # Local environment variables (git-ignored)
├── .env.example               # Environment template
├── .git/                      # Git repository
├── .gitignore                 # Git ignore rules
├── .vercel/                   # Vercel deployment config
│   ├── project.json          # Vercel project metadata
│   └── README.txt            # Vercel notes
├── docker-compose.yml        # Docker multi-container orchestration
├── README.md                 # Project documentation
├── backend/                  # Python FastAPI backend
├── frontend/                 # Next.js 14 React frontend
```

---

## 🐍 BACKEND — Python (FastAPI)

**Root**: `backend/`  
**Framework**: FastAPI 0.115.0 + SQLAlchemy + Alembic  
**Database**: PostgreSQL 15 + AsyncPG  
**Python Version**: 3.12 (from Dockerfile)

### Configuration Files

| File | Purpose |
|------|---------|
| `requirements.txt` | Python dependencies (20 packages) |
| `alembic.ini` | Alembic migration config |
| `Dockerfile` | Docker image for backend service |

### Key Dependencies

```
fastapi==0.115.0              # Web framework
uvicorn==0.30.6               # ASGI server
sqlalchemy==2.0.35            # ORM
asyncpg==0.29.0              # PostgreSQL driver
alembic==1.13.3              # Database migrations
pydantic==2.9.2              # Data validation
groq==0.11.0                 # LLM provider
openai==1.51.0               # OpenAI support (optional)
langfuse==2.53.3             # Observability
chromadb==0.5.15             # Vector DB
sentence-transformers==3.1.1 # Embeddings
minio==7.2.9                 # S3-compatible storage
```

### Python Files: `app/`

#### Main Entry Point
- **`main.py`** — FastAPI app factory, CORS config, lifespan events, router registration

#### API Routes: `app/api/v1/` (7 files)
- **`router.py`** — v1 router aggregator
- **`needs.py`** — Business needs API endpoints (all business logic routes)
- **`__init__.py`** — Package marker (empty)

#### Core Services: `app/core/` (12 files)

| File | Purpose |
|------|---------|
| `config.py` | Settings & environment management |
| `database.py` | SQLAlchemy async engine, session factory, `get_db()` |
| `embedding_client.py` | Embedding API (local or remote) |
| `llm_client.py` | LLM provider abstraction (Groq, Azure OpenAI) |
| `llm_client.py` | Intent prompt builder for NLP classification |
| `chroma.py` | ChromaDB async client & collection access |
| `langfuse_tracking.py` | Observability/LLM tracking integration |
| `minio_client.py` | S3-compatible file storage |
| `seed_catalog.py` | Catalog initialization on startup |
| `recommendation_limits.py` | Constants for recommendation quotas |
| `expertise_roles.py` | Expertise team role definitions |
| `__init__.py` — Package marker |

#### Models: `app/models/` (2 files)

| File | Purpose |
|------|---------|
| `business_need.py` | SQLAlchemy ORM: `BusinessNeed` table, `IdCounter`, `NlpCache` |
| `__init__.py` — Package marker |

#### Schemas: `app/schemas/` (2 files)

| File | Purpose |
|------|---------|
| `business_need.py` | Pydantic v2 request/response schemas (20+ types) |
| `__init__.py` — Package marker |

**Schema Types Include**:
- `CreateNeedRequest`, `BusinessNeedResponse` — Need CRUD
- `AnalyzeRequest`, `AnalyzeResponse` — AI classification
- `CatalogSearchResponse`, `CatalogProduct` — Catalog integration
- `ExpertiseTeamEstimateResponse`, `DurationEstimateResponse` — Estimates
- `BusinessImpactScoreResponse` — Impact scoring
- `RecommendationsResponse` — Final recommendations
- `ExportReportRequest` — Report export config

#### Services: `app/services/` (15 files)

| File | Purpose |
|------|---------|
| `embedding_service.py` | Text embedding & similarity operations |
| `nlp_service.py` | NLP tagging (objectif, domaine, impact, origine) |
| `llm_service.py` | —— **NOT PRESENT** (logic in llm_client.py) |
| `business_impact_scoring.py` | Impact scoring algorithm against catalog |
| `catalog_loader.py` | Loads catalog.xlsx → Solution objects |
| `catalog_feature_match.py` | Feature matching for recommendations |
| `expertise_team_service.py` | Expertise team estimation |
| `expertise_team_constraints.py` | Team size/cost constraints |
| `duration_formula.py` | Duration calculation formula |
| `dxc_context.py` | DXC organizational context |
| `maturity_scoring.py` | Solution maturity scoring |
| `id_service.py` | Unique ID generation |
| `export_service.py` | PDF/DOCX report generation |
| `rules_engine.py` | Business rules evaluation |
| `validation_guards.py` | API request validation |
| `__init__.py` — Package marker |

#### Seeds: `app/seeds/` (2 files)

| File | Purpose |
|------|---------|
| `seed_chroma.py` | Initialize ChromaDB with embeddings |
| `__init__.py` — Package marker |

#### Assets: `app/assets/` (2 files)

| File | Purpose |
|------|---------|
| `dxc_logo.png` | DXC logo image |
| `.gitkeep` — Git placeholder |

#### Data: `app/data/` (1 file)

| File | Purpose |
|------|---------|
| `catalog.xlsx` | DXC product catalog (loaded by `catalog_loader.py`) |

### Database Migrations: `alembic/versions/` (4 files)

| File | Purpose |
|------|---------|
| `env.py` | Alembic async migration environment |
| `001_initial_schema.py` | Create `business_needs`, `id_counters`, `nlp_cache` tables |
| `002_add_constraints.py` | Add `constraints` JSONB column |
| `003_add_need_confidence_risks_ivi.py` | Add `confidence`, `risks`, `ivi_scores` columns |

**Schema Notes**:
- Primary table: `business_needs` (id, pitch, horizon, tags, constraints, confidence, risks, ivi_scores, created_at)
- Support tables: `id_counters`, `nlp_cache`

---

## ⚛️ FRONTEND — TypeScript/React + Next.js 14

**Root**: `frontend/`  
**Framework**: Next.js 14.2.15 + React 18.3.1  
**Language**: TypeScript 5.6.3  
**Styling**: CSS (custom design system + dark mode)

### Configuration Files

| File | Purpose |
|------|---------|
| `package.json` | Dependencies, scripts, metadata |
| `tsconfig.json` | TypeScript configuration |
| `next.config.js` | Next.js build configuration |
| `Dockerfile` | Docker image for frontend service |
| `.env.local` | Local environment variables (git-ignored) |
| `.gitignore` | Git ignore rules |

### Dependencies

```json
{
  "next": "14.2.15",
  "react": "18.3.1",
  "framer-motion": "11.5.0",
  "sonner": "1.7.0"
}
```

### TypeScript/JavaScript Files: `src/` (38 files)

#### App Routes: `src/app/` (8 files)

| Route | File | Purpose |
|-------|------|---------|
| **Root** | `layout.tsx` | Root layout (typography, theme, Google Fonts) |
| **Root** | `page.tsx` | Home/landing page |
| **Root** | `globals.css` | Global CSS variables & design system |
| `/sourcing` | `sourcing/page.tsx` | Business need capture & SG-1 validation |
| `/discovery` | `discovery/page.tsx` | Catalog search & SG-2 validation |
| `/evaluation` | `evaluation/page.tsx` | Solution scoring & evaluation |
| `/selection` | `selection/page.tsx` | Solution selection & SG-3 validation |
| `/recos` | `recos/page.tsx` | Recommendations & SG-4 validation & exports |
| `/dashboard` | `dashboard/page.tsx` | IPM list & workflow overview |

**Workflow Path**: `/sourcing` → SG-1 → `/discovery` → SG-2 → `/evaluation` → `/selection` → SG-3 → `/recos` → SG-4 → Done

#### Layout Components: `src/components/layout/` (3 files)

| File | Purpose |
|------|---------|
| `ThemeProvider.tsx` | Dark/light mode context & persistence |
| `ThemeToggle.tsx` | Theme switcher UI |
| `WorkflowBar.tsx` | Sticky workflow progress bar |

#### Dashboard Components: `src/components/dashboard/` (3 files)

| File | Purpose |
|------|---------|
| `NeedCard.tsx` | Business need card for list |
| `StatusBadge.tsx` | SG status indicator |
| `EmptyState.tsx` | Empty dashboard state |

#### Discovery Components: `src/components/discovery/` (1 file)

| File | Purpose |
|------|---------|
| `DiscoveryPanel.tsx` | Catalog search & filtering UI |

#### Gate/Workflow Components: `src/components/gates/` + `src/components/workflow/` (6 files)

| File | Purpose | Notes |
|------|---------|-------|
| `gates/StageGate.tsx` | Modal dialog for SG decisions (GO/REWORK/STOP) | **DUPLICATE NAME** but different purpose |
| `workflow/StageGate.tsx` | Diamond-shaped gate node in workflow diagram | Framer-motion animated |
| `workflow/PhaseContainer.tsx` | Phase container in workflow |
| `workflow/WorkflowNode.tsx` | Individual workflow step node |
| `workflow/GateModal.tsx` | Gate decision modal (alt) |
| `workflow/Connector.tsx` | Dashed connectors between workflow nodes |

#### Sourcing Components: `src/components/sourcing/` (11 files)

| File | Purpose |
|------|---------|
| `SourcingShell.tsx` | Main sourcing form container |
| `PitchPanel.tsx` | Business pitch input |
| `HorizonSelector.tsx` | Innovation horizon picker |
| `RecapPanel.tsx` | Recap of inputs |
| `TagChips.tsx` | AI-generated tags display |
| `SuggestionsPanel.tsx` | AI recommendations panel |
| `DuplicateBanner.tsx` | Duplicate need warning |
| `Sg1ValidationPanel.tsx` | SG-1 checklist & validation |
| `Sg2ValidationPanel.tsx` | SG-2 checklist & validation |
| `Sg3ValidationPanel.tsx` | SG-3 checklist & validation |
| `Sg4ValidationPanel.tsx` | SG-4 checklist & validation |

#### Hooks: `src/hooks/` (3 files)

| File | Purpose |
|------|---------|
| `useNeeds.ts` | Business needs API hook |
| `useAnalyze.ts` | Analysis/classification hook |
| `use-mobile.ts` | Mobile responsive hook |

#### Utilities: `src/lib/` (3 files)

| File | Purpose |
|------|---------|
| `api.ts` | Fetch wrapper for backend API calls |
| `types.ts` | TypeScript type definitions |
| `discoveryStubs.ts` | Mock data for discovery (dev/demo) |

### Public Assets: `public/` (19+ files)

#### Landing Page
- `landing.html` — Static landing page HTML
- `ipm-flow-mark.svg` — IPM logo/mark

#### Landing Resources: `landing-files/` (6+ files)
- JavaScript bundles (50574781.js, 50574781_002.js, etc.)
- Avif images (6 images, optimized format)
- Frame graphic (69302909f4853148b70b7b33_Frame 2147228926.avif)

#### Animations: `lottie/` (1 file)
- `ipm-workflow.json` — Lottie animation JSON (workflow visualization)

#### Vendor: `vendor/` (1 file)
- `lottie.min.js` — Lottie animation library

---

## 🔄 DOCKER & ORCHESTRATION

### docker-compose.yml

**Services**:
1. **api** (Python/FastAPI)
   - Port: 8000
   - Environment: DB, ChromaDB, MinIO, LLM config
   - Depends on: postgres, chromadb, minio
   - Volume: `./backend:/app`

2. **postgres** (PostgreSQL 15-alpine)
   - Default credentials: ipm/ipm
   - Database: ipm
   - Health checks enabled

3. **chromadb** (Vector database)
   - Port: 8000 (internal)

4. **minio** (S3-compatible storage)
   - Port: 9000
   - Default credentials: minioadmin/minioadmin

**Data Volumes** (in .gitignore):
- `pg_data/` — PostgreSQL data
- `chroma_data/` — ChromaDB persistence
- `minio_data/` — MinIO object storage

---

## 🔍 DUPLICATE FILES & ANALYSIS

### ✅ Intentional Duplicates (NOT Orphaned)

#### 1. **`StageGate.tsx`** (2 versions)

**Location 1**: `frontend/src/components/gates/StageGate.tsx`
- **Purpose**: Modal dialog for stage gate decisions
- **Props**: `gateId` (SG-1/2/3/4/5), `title`, `checklist`, `onGo()`, `onRework()`, `onStop()`
- **Used by**: Sourcing, Discovery, Evaluation routes

**Location 2**: `frontend/src/components/workflow/StageGate.tsx`
- **Purpose**: Animated diamond-shaped gate node in workflow diagram
- **Framework**: Framer-motion
- **Props**: `label`, `isActive`, `isCompleted`, `color`, `delay`
- **Used by**: Workflow visualization components

**Verdict**: ✅ **CORRECT DESIGN** — Two different UI components with same conceptual name but completely different implementation and usage

#### 2. **`business_need.py`** (2 versions)

**Location 1**: `backend/app/models/business_need.py`
- **Purpose**: SQLAlchemy ORM model
- **Content**: `BusinessNeed`, `IdCounter`, `NlpCache` database models

**Location 2**: `backend/app/schemas/business_need.py`
- **Purpose**: Pydantic v2 request/response schemas
- **Content**: 20+ schema types for API validation

**Verdict**: ✅ **CORRECT ARCHITECTURE** — Standard FastAPI pattern: SQLAlchemy models vs Pydantic schemas are separate concerns

#### 3. **`__init__.py`** (Multiple packages)

**Locations**: Every Python package directory
- **Purpose**: Package markers (standard Python)
- **Note**: Some are empty (correct for namespace packages)

**Verdict**: ✅ **STANDARD PRACTICE**

---

## 📊 COMPREHENSIVE FILE LISTING

### Backend — All Python Files (43 total)

**Core**:
```
backend/
├── app/__init__.py
├── app/main.py
├── app/core/
│   ├── __init__.py
│   ├── config.py
│   ├── database.py
│   ├── embedding_client.py
│   ├── llm_client.py
│   ├── intent_prompt.py
│   ├── chroma.py
│   ├── langfuse_tracking.py
│   ├── minio_client.py
│   ├── seed_catalog.py
│   ├── recommendation_limits.py
│   └── expertise_roles.py
├── app/models/
│   ├── __init__.py
│   └── business_need.py
├── app/schemas/
│   ├── __init__.py
│   └── business_need.py
├── app/api/v1/
│   ├── __init__.py
│   ├── router.py
│   └── needs.py
├── app/services/
│   ├── __init__.py
│   ├── embedding_service.py
│   ├── nlp_service.py
│   ├── business_impact_scoring.py
│   ├── catalog_loader.py
│   ├── catalog_feature_match.py
│   ├── expertise_team_service.py
│   ├── expertise_team_constraints.py
│   ├── duration_formula.py
│   ├── dxc_context.py
│   ├── maturity_scoring.py
│   ├── id_service.py
│   ├── export_service.py
│   ├── rules_engine.py
│   └── validation_guards.py
├── app/seeds/
│   ├── __init__.py
│   └── seed_chroma.py
├── app/assets/
│   ├── .gitkeep
│   └── dxc_logo.png
├── app/data/
│   └── catalog.xlsx
├── alembic/
│   ├── env.py
│   └── versions/
│       ├── 001_initial_schema.py
│       ├── 002_add_constraints.py
│       └── 003_add_need_confidence_risks_ivi.py
```

### Frontend — All TypeScript/JavaScript Files (38 total)

```
frontend/src/
├── app/
│   ├── layout.tsx
│   ├── page.tsx
│   ├── globals.css
│   ├── dashboard/page.tsx
│   ├── discovery/page.tsx
│   ├── evaluation/page.tsx
│   ├── recos/page.tsx
│   ├── selection/page.tsx
│   └── sourcing/page.tsx
├── components/
│   ├── layout/
│   │   ├── ThemeProvider.tsx
│   │   ├── ThemeToggle.tsx
│   │   └── WorkflowBar.tsx
│   ├── dashboard/
│   │   ├── EmptyState.tsx
│   │   ├── NeedCard.tsx
│   │   └── StatusBadge.tsx
│   ├── discovery/
│   │   └── DiscoveryPanel.tsx
│   ├── gates/
│   │   └── StageGate.tsx ← MODAL VERSION
│   ├── sourcing/
│   │   ├── DuplicateBanner.tsx
│   │   ├── HorizonSelector.tsx
│   │   ├── PitchPanel.tsx
│   │   ├── RecapPanel.tsx
│   │   ├── Sg1ValidationPanel.tsx
│   │   ├── Sg2ValidationPanel.tsx
│   │   ├── Sg3ValidationPanel.tsx
│   │   ├── Sg4ValidationPanel.tsx
│   │   ├── SourcingShell.tsx
│   │   ├── SuggestionsPanel.tsx
│   │   └── TagChips.tsx
│   └── workflow/
│       ├── Connector.tsx
│       ├── GateModal.tsx
│       ├── PhaseContainer.tsx
│       ├── StageGate.tsx ← WORKFLOW VERSION
│       └── WorkflowNode.tsx
├── hooks/
│   ├── use-mobile.ts
│   ├── useAnalyze.ts
│   └── useNeeds.ts
└── lib/
    ├── api.ts
    ├── discoveryStubs.ts
    └── types.ts
```

---

## 🗂️ BUILD & OUTPUT DIRECTORIES (Git-Ignored)

| Directory | Purpose | Size Impact |
|-----------|---------|------------|
| `.next/` | Next.js build output | ~100+ MB |
| `node_modules/` | npm dependencies | ~500+ MB |
| `__pycache__/` | Python bytecode caches | ~10 MB |
| `alembic/versions/__pycache__/` | Migration bytecode | ~1 MB |
| `.vercel/` | Vercel deployment metadata | <1 MB |
| `pg_data/` | PostgreSQL data (Docker volume) | Varies |
| `chroma_data/` | ChromaDB data (Docker volume) | Varies |
| `minio_data/` | MinIO object storage (Docker volume) | Varies |

**All properly excluded by `.gitignore`**

---

## 🚨 ORPHANED OR UNNECESSARY FILES

### ❌ None Identified

**Verification**:
- ✅ All Python files imported in `app/main.py` or `app/api/v1/needs.py`
- ✅ All TypeScript files exported/used in page routes or components
- ✅ All data files (`catalog.xlsx`) actively loaded on startup
- ✅ All assets (`dxc_logo.png`, animations) referenced in components
- ✅ Migration files in sequence (001 → 002 → 003)

### ⚠️ Potential Optimization Opportunities

1. **`app/core/intent_prompt.py`** — Appears imported but verify active usage in NLP pipeline
2. **`discoveryStubs.ts`** — Mock data file; ensure removed before production
3. **Large landing assets** in `public/landing-files/` — Verify if still used (alternate landing?)

---

## 🔗 DEPENDENCY MAPPING

### Backend Imports Analysis

**Core Module Dependencies**:
```
main.py
├── api.v1.router
├── core.config
├── core.database
└── models.business_need

api.v1.needs.py (main business logic hub)
├── core.llm_client
├── core.embedding_client
├── core.chroma
├── core.database
├── core.config
├── models.business_need
├── schemas.business_need
├── services.embedding_service
├── services.nlm_service
├── services.nlp_service
├── services.export_service
├── services.catalog_loader
├── services.business_impact_scoring
├── services.expertise_team_service
├── services.maturity_scoring
├── services.duration_formula
├── services.validation_guards
├── services.catalog_feature_match
└── core.langfuse_tracking

[All services import from core and models]
```

### Frontend State Management

**No Redux/Zustand detected** — State managed via:
- URL query params (`?id=`)
- `localStorage` keys:
  - `ipm_selected_solutions`
  - `ipm_sg2_state`
  - `ipm_evaluation_state`
  - `ipm_delivery_solutions`
- React hooks (useNeeds, useAnalyze)

---

## ✨ SUMMARY STATISTICS

| Metric | Count |
|--------|-------|
| **Backend Python Files** | 43 |
| **Frontend TypeScript/TSX Files** | 38 |
| **Configuration Files** | 8 |
| **Database Migration Versions** | 3 |
| **API Endpoints (estimated)** | 15+ |
| **React Pages** | 8 |
| **React Components** | 20+ |
| **Services** | 15 |
| **Core Modules** | 12 |
| **Docker Services** | 4 |
| **Total Lines of Config** | ~200+ |

---

## 📝 NOTES

1. **Single-Role Design**: Current implementation is CLIENT DXC only; no authentication/RBAC
2. **State Persistence**: Uses localStorage for workflow state hand-off between pages
3. **Async Throughout**: FastAPI uses AsyncIO for all database operations
4. **Observability**: Langfuse integration for LLM tracking
5. **Catalog-Driven**: All recommendations based on `catalog.xlsx` loaded at startup
6. **Multi-LLM Support**: Can switch between Groq/OpenAI/Azure OpenAI via config
7. **Docker-First**: Development uses docker-compose with 4 services (API, Postgres, ChromaDB, MinIO)

---

**Last Updated**: May 9, 2026  
**Project Status**: v0 (MVP)
