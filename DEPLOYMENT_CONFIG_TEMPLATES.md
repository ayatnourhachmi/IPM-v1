# Configuration Templates for Cloud Deployment

This file contains ready-to-use configuration templates to speed up your deployment.

---

## 1. Backend .env.example

**File:** `backend/.env.example`

```bash
# ============================================================================
# DATABASE CONFIGURATION (Supabase)
# ============================================================================
DATABASE_URL=postgresql+asyncpg://postgres:password@db.supabase.co:5432/postgres
# Format: postgresql+asyncpg://user:password@host:port/database

# ============================================================================
# VECTOR DATABASE (Pinecone)
# ============================================================================
PINECONE_API_KEY=your-pinecone-api-key-here
PINECONE_ENVIRONMENT=us-east1-gcp
# Available regions: us-east1-gcp, us-west1-gcp, us-central1-aws, eu-west1-aws, etc.

# ============================================================================
# OBJECT STORAGE (AWS S3)
# ============================================================================
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_S3_BUCKET=ipm-storage
AWS_REGION=us-east-1

# ============================================================================
# LLM & EMBEDDING SERVICES
# ============================================================================
LLM_PROVIDER=groq
GROQ_API_KEY=your-groq-api-key
EMBEDDING_PROVIDER=sentence-transformers
# Alternative: huggingface (requires HUGGINGFACE_API_KEY)

HUGGINGFACE_API_KEY=your-hf-key  # Optional if using HF embeddings

# ============================================================================
# MONITORING & OBSERVABILITY (Langfuse)
# ============================================================================
LANGFUSE_PUBLIC_KEY=your-langfuse-public-key
LANGFUSE_SECRET_KEY=your-langfuse-secret-key
LANGFUSE_HOST=https://cloud.langfuse.com

# ============================================================================
# APPLICATION SETTINGS
# ============================================================================
ENVIRONMENT=production
DEBUG=false

# CORS settings
ALLOWED_ORIGINS=https://ipm.vercel.app,http://localhost:3000

# API settings
API_PREFIX=/api/v1
API_TITLE=IPM API
API_VERSION=1.0.0
```

---

## 2. Frontend .env.example

**File:** `frontend/.env.example`

```bash
# ============================================================================
# API CONFIGURATION
# ============================================================================
NEXT_PUBLIC_API_URL=https://ipm-api.onrender.com
# For development: http://localhost:8000

# ============================================================================
# ANALYTICS & MONITORING (Optional)
# ============================================================================
NEXT_PUBLIC_ENABLE_ANALYTICS=true
NEXT_PUBLIC_SENTRY_DSN=  # Optional: for error tracking

# ============================================================================
# FEATURE FLAGS (Optional)
# ============================================================================
NEXT_PUBLIC_ENABLE_EXPORT=true
NEXT_PUBLIC_ENABLE_RECOMMENDATIONS=true
```

---

## 3. render.yaml

**File:** `render.yaml`

```yaml
services:
  # Backend API Service
  - type: web
    name: ipm-api
    env: python
    plan: free
    runtime: python-3.11
    region: ohio  # Render region closest to your users
    
    buildCommand: >
      pip install -r requirements.txt && 
      alembic upgrade head &&
      alembic current
    
    startCommand: >
      uvicorn app.main:app 
      --host 0.0.0.0 
      --port $PORT 
      --workers 1 
      --loop uvloop 
      --http h11
    
    healthCheckPath: /health
    
    envVars:
      # Database
      - key: DATABASE_URL
        sync: false
      
      # Vector DB
      - key: PINECONE_API_KEY
        sync: false
      - key: PINECONE_ENVIRONMENT
        value: us-east1-gcp
      
      # Storage
      - key: AWS_ACCESS_KEY_ID
        sync: false
      - key: AWS_SECRET_ACCESS_KEY
        sync: false
      - key: AWS_S3_BUCKET
        value: ipm-storage
      - key: AWS_REGION
        value: us-east-1
      
      # LLM
      - key: LLM_PROVIDER
        value: groq
      - key: GROQ_API_KEY
        sync: false
      - key: EMBEDDING_PROVIDER
        value: sentence-transformers
      
      # Monitoring
      - key: LANGFUSE_PUBLIC_KEY
        sync: false
      - key: LANGFUSE_SECRET_KEY
        sync: false
      - key: LANGFUSE_HOST
        value: https://cloud.langfuse.com
      
      # App
      - key: ENVIRONMENT
        value: production
      - key: DEBUG
        value: false
      - key: PYTHONUNBUFFERED
        value: true

databases:
  - name: ipm
    plan: free
```

---

## 4. Docker Compose for Local Development

**File:** `docker-compose.yml` (Updated for local development)

```yaml
version: '3.9'

services:
  api:
    build: ./backend
    ports: ["8000:8000"]
    environment:
      - DATABASE_URL=postgresql+asyncpg://ipm:ipm@postgres:5432/ipm
      - MINIO_ENDPOINT=minio:9000
      - MINIO_ACCESS_KEY=minioadmin
      - MINIO_SECRET_KEY=minioadmin
      - LLM_PROVIDER=groq
      - GROQ_API_KEY=${GROQ_API_KEY}
      - LANGFUSE_PUBLIC_KEY=${LANGFUSE_PUBLIC_KEY}
      - LANGFUSE_SECRET_KEY=${LANGFUSE_SECRET_KEY}
      - LANGFUSE_HOST=https://cloud.langfuse.com
      - EMBEDDING_PROVIDER=local
      - ENVIRONMENT=development
      - DEBUG=true
      - PINECONE_API_KEY=${PINECONE_API_KEY}
      - PINECONE_INDEX=${PINECONE_INDEX:-ipm-local}
      - PINECONE_AUTO_CREATE_INDEX=${PINECONE_AUTO_CREATE_INDEX:-true}
      - PINECONE_SEED_CATALOG_ON_STARTUP=true
    depends_on:
      postgres:
        condition: service_healthy
      minio:
        condition: service_started
    volumes:
      - ./backend:/app
    networks:
      - ipm-network

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: ipm
      POSTGRES_PASSWORD: ipm
      POSTGRES_DB: ipm
    ports: ["5432:5432"]
    volumes:
      - pg_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ipm"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - ipm-network

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    volumes:
      - minio_data:/data
    networks:
      - ipm-network

  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    depends_on:
      - api
    volumes:
      - ./frontend:/app
      - /app/node_modules
      - /app/.next
    networks:
      - ipm-network

volumes:
  pg_data:
  minio_data:

networks:
  ipm-network:
    driver: bridge
```

---

## 5. Vercel Deployment Configuration

**File:** `vercel.json`

```json
{
  "buildCommand": "npm run build",
  "outputDirectory": ".next",
  "functions": {
    "frontend/pages/api/**": {
      "memory": 1024,
      "maxDuration": 60
    }
  },
  "env": {
    "NEXT_PUBLIC_API_URL": "@next_public_api_url"
  },
  "public": false
}
```

---

## 6. GitHub Actions CI/CD (Optional)

**File:** `.github/workflows/deploy.yml`

```yaml
name: Deploy IPM

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install backend dependencies
        run: |
          cd backend
          pip install -r requirements.txt
      
      - name: Lint backend
        run: |
          cd backend
          pip install ruff
          ruff check .
      
      - name: Set up Node
        uses: actions/setup-node@v3
        with:
          node-version: '20'
      
      - name: Install frontend dependencies
        run: |
          cd frontend
          npm ci
      
      - name: Build frontend
        run: |
          cd frontend
          npm run build

  deploy-backend:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to Render
        run: |
          curl -X POST "https://api.render.com/deploy/srv-${{ secrets.RENDER_SERVICE_ID }}" \
            -H "authorization: Bearer ${{ secrets.RENDER_API_KEY }}"

  deploy-frontend:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to Vercel
        env:
          VERCEL_TOKEN: ${{ secrets.VERCEL_TOKEN }}
        run: |
          npm i -g vercel
          cd frontend
          vercel deploy --prod --token $VERCEL_TOKEN
```

---

## 7. Makefile for Local Development

**File:** `Makefile`

```makefile
.PHONY: help install dev stop clean migrate seed

help:
	@echo "IPM Development Commands"
	@echo ""
	@echo "  make install      - Install all dependencies"
	@echo "  make dev          - Start local development environment"
	@echo "  make stop         - Stop all services"
	@echo "  make clean        - Clean up volumes and containers"
	@echo "  make migrate      - Run database migrations"
	@echo "  make seed         - Seed database with sample data"
	@echo "  make logs         - View Docker logs"
	@echo "  make backend-lint - Lint backend code"
	@echo "  make frontend-lint- Lint frontend code"

install:
	@echo "Installing dependencies..."
	cd backend && pip install -r requirements.txt
	cd frontend && npm install

dev:
	@echo "Starting development environment..."
	docker-compose up -d
	@echo "Services starting:"
	@echo "  Frontend:  http://localhost:3000"
	@echo "  Backend:   http://localhost:8000"
	@echo "  API Docs:  http://localhost:8000/docs"
	@echo "  MinIO:     http://localhost:9001"
	@echo "  Pinecone:  vectors hosted in Pinecone (${PINECONE_INDEX:-unset index})"

stop:
	@echo "Stopping all services..."
	docker-compose down

clean:
	@echo "Removing volumes and containers..."
	docker-compose down -v
	@echo "Cleaned up!"

migrate:
	@echo "Running migrations..."
	docker exec ipm-v0-api-1 alembic upgrade head

seed:
	@echo "Re-seeding Pinecone namespaces (needs compose env PINECONE_*) ..."
	docker compose exec api python -c "from app.core.seed_catalog import seed_catalog; seed_catalog()"
	docker compose exec api python -c "from app.seeds.seed_pinecone import seed_demo_business_needs; seed_demo_business_needs()"

logs:
	docker-compose logs -f

backend-lint:
	@echo "Linting backend..."
	cd backend && pip install ruff && ruff check .

frontend-lint:
	@echo "Linting frontend..."
	cd frontend && npm run lint

test:
	@echo "Running tests..."
	cd backend && pytest
	cd frontend && npm run test
```

---

## 8. Environment Variables Quick Reference

### For Supabase
```
Go to: https://supabase.com/dashboard/project/[YOUR_PROJECT]/settings/database

Connection string example:
postgresql+asyncpg://postgres:[password]@db.[region].supabase.co:5432/postgres
```

### For Pinecone
```
Go to: https://app.pinecone.io/

1. Settings → API Keys → copy PINECONE_API_KEY
2. Create a serverless index: metric cosine, dimension 384 (BGE-small-en-v1.5 default)
   Set PINECONE_INDEX to that index name.
3. Set PINECONE_REGION / PINECONE_CLOUD (e.g. us-east-1 + aws) if using auto-create
   (PINECONE_AUTO_CREATE_INDEX=true), or match the console region manually.
Namespaces `business_needs` and `dxc_catalog` are created on first upsert by the API.
```

### For AWS S3
```
Go to: https://console.aws.amazon.com/iam/

1. Create new IAM user
2. Attach policy: AmazonS3FullAccess (or limit to specific bucket)
3. Generate access keys
```

### For Groq API
```
Go to: https://console.groq.com/

1. Create account
2. Get API key from dashboard
3. Check rate limits (free tier: adjust as needed)
```

### For Langfuse
```
Go to: https://cloud.langfuse.com/

1. Create project
2. Get keys from settings
3. These are for production monitoring (optional)
```

### For Render
```
Go to: https://dashboard.render.com/

1. Create new web service
2. Connect GitHub repository
3. Render will pull env vars from render.yaml
```

### For Vercel
```
Go to: https://vercel.com/

1. Import project
2. Set environment variables in project settings
3. Deploy automatically on push to main
```

---

## 9. Database Schema Reset (Emergency Only)

If you need to reset everything:

```sql
-- On Supabase SQL Editor
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO anon;
GRANT ALL ON SCHEMA public TO authenticated;
GRANT ALL ON SCHEMA public TO service_role;

-- Then run alembic migrations
-- alembic upgrade head
```

---

## ✅ Configuration Checklist

- [ ] Create `.env.example` in backend/
- [ ] Create `.env.example` in frontend/
- [ ] Create actual `.env` files (add to `.gitignore`)
- [ ] Create `render.yaml` in project root
- [ ] Create `vercel.json` in project root
- [ ] Create Makefile in project root
- [ ] Update `docker-compose.yml`
- [ ] Update `backend/requirements.txt` (pinecone SDK + embeddings stack)
- [ ] Set up GitHub Actions workflows
- [ ] Get all API keys and service credentials
- [ ] Test locally with docker-compose
- [ ] Deploy to Render
- [ ] Deploy to Vercel
- [ ] Monitor in Langfuse dashboard

---

**All configuration files are ready to use. Copy and customize for your needs!**
