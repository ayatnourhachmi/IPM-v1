# 🚀 FREE Deployment Migration Guide: From Local Docker to Cloud

Complete step-by-step guide to deploy IPM on free tier services.

## How To Use This Guide

Follow the phases in order. Do not skip ahead until the current phase is complete.

1. Prepare the repo for cloud deployment.
2. Create the free-tier cloud services.
3. Update the backend for cloud settings.
4. Update the frontend for the deployed API URL.
5. Deploy backend first, then frontend.
6. Verify the deployment and fix any startup issues.

## What Needs Your Intervention

You will need to step in for anything that depends on your own accounts, credentials, or approval decisions.

Required from you:

1. Create or sign in to Supabase, Pinecone, AWS, Render, and Vercel.
2. Generate and paste the API keys and connection strings.
3. Decide the final service names, bucket names, and project names.
4. Confirm whether you want to keep any local services instead of replacing them.
5. Deploy the services from your cloud dashboards if you do not want to use the CLI.

Not required from you if I am editing the repo:

1. I can update the deployment guide and config files.
2. I can prepare code changes for environment variables, Dockerfiles, and deployment manifests.
3. I can help validate the file structure and deployment instructions.

---

## 📋 Architecture Overview

### Current (Local Docker)
```
┌─────────────────┐
│   Your Machine  │
├─────────────────┤
│ Frontend (3000) │
│ Backend (8000)  │  → PostgreSQL (5432)
│ ChromaDB (8001) │  → MinIO (9000)
│ MinIO Console   │  → Langfuse
└─────────────────┘
```

### Target (Free Cloud)
```
┌──────────────────────────────────────────────────┐
│           Cloud Deployment                       │
├──────────────────────────────────────────────────┤
│ Frontend: Vercel (Free)        → UI Hosting      │
│ Backend: Render.com (Free)     → API Server      │
│ Database: Neon (Free)          → PostgreSQL      │
│ Vector DB: Pinecone (Free)     → Embeddings      │
└──────────────────────────────────────────────────┘
```

---

## 🎯 Step-by-Step Migration Plan

## Phase 1: Prepare Code for Cloud Deployment

Complete these steps in order before moving to Phase 2.

1. Create the environment example files.
2. Update the Dockerfiles for cloud builds.
3. Add the migration startup script.

### Step 1.1: Update Environment Configuration

Do this first so every later deployment setting has a documented home.

Create `backend/.env.example`:
```bash
# Database (Supabase)
DATABASE_URL=postgresql+asyncpg://user:password@db.supabase.co:5432/postgres

# Vector DB (Pinecone)
PINECONE_API_KEY=your-key
PINECONE_ENVIRONMENT=us-east1-gcp  # or your region

# Storage (AWS S3)
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_S3_BUCKET=ipm-storage
AWS_REGION=us-east-1

# LLM & Monitoring
GROQ_API_KEY=your-key
LANGFUSE_PUBLIC_KEY=your-key
LANGFUSE_SECRET_KEY=your-key
EMBEDDING_PROVIDER=sentence-transformers  # Keep local for free tier

# Deployment
ENVIRONMENT=production
DEBUG=false
```

Create `frontend/.env.example`:
```bash
# API endpoint (will be Render URL)
NEXT_PUBLIC_API_URL=https://ipm-api.onrender.com
```

Verify: both example files exist and contain only placeholder or default values.

### Step 1.2: Update Docker Configuration

Do this second so the backend and frontend images are ready for cloud deploys.

Create `backend/Dockerfile` optimizations:
```dockerfile
# Multi-stage build for smaller image size
FROM python:3.11-slim as builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Final stage
FROM python:3.11-slim
WORKDIR /app

COPY --from=builder /root/.local /root/.local
COPY app/ app/
COPY alembic/ alembic/
COPY alembic.ini .

ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Update `frontend/Dockerfile` for Next.js:
```dockerfile
FROM node:20-alpine AS base

WORKDIR /app
COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM node:20-alpine
WORKDIR /app
COPY --from=base /app/public ./public
COPY --from=base /app/.next/standalone ./
COPY --from=base /app/.next/static ./.next/static

ENV NODE_ENV=production
EXPOSE 3000

CMD ["node", "server.js"]
```

Verify: each Dockerfile still installs dependencies and starts the app with a single production command.

### Step 1.3: Prepare Databases

Do this last in Phase 1 so the app can wait for the database before running migrations.

Create migration script `backend/migrate.sh`:
```bash
#!/bin/bash
set -e

# Wait for database to be ready
echo "Waiting for database..."
python -c "
import time
from sqlalchemy import text
from app.core.database import engine
import asyncio

async def check_db():
    for i in range(30):
        try:
            async with engine.connect() as conn:
                await conn.execute(text('SELECT 1'))
            print('Database connected!')
            break
        except:
            print(f'Attempt {i+1}/30 - waiting...')
            await asyncio.sleep(2)

asyncio.run(check_db())
"

# Run migrations
alembic upgrade head

echo "Migrations complete!"
```

Verify: the script waits for PostgreSQL, then runs `alembic upgrade head`.

---

## Phase 2: Set Up Free Cloud Services

### Your Stack: Neon + Render + Vercel + Pinecone

#### Service 1: Neon (PostgreSQL)
**Free Tier:** 3 projects, 0.5 GB storage, unlimited queries

```bash
# 1. Go to https://neon.tech → Sign up (free)
# 2. Create a new project
# 3. Go to Connection string (default role)
# 4. Copy the full PostgreSQL connection string
# 5. The format is: postgresql://[user]:[password]@[host]/[database]?sslmode=require
```

#### Service 2: Pinecone (Vector Database)
**Free Tier:** 1 free pod for vector search, 1M vectors

```bash
# 1. Go to https://pinecone.io → Sign up (free)
# 2. Create API key
# 3. Create index "ipm-vectors" (dimension: 384 for sentence-transformers)
# 4. Note your environment (e.g., us-east1-gcp)
```

#### Service 3: Render (Backend API)
**Free Tier:** 0.5 vCPU, 512MB RAM, 100GB bandwidth/month, auto-sleeps after 15 min

```bash
# 1. Go to https://render.com → Sign up (free)
# 2. Connect your GitHub account
# 3. Create new → Web Service (link your repo)
# 4. Name: ipm-api
# 5. You'll set environment variables in the Render dashboard after deploy
```

#### Service 4: Vercel (Frontend)
**Free Tier:** Unlimited deployments, 100GB bandwidth/month

```bash
# 1. Go to https://vercel.com → Sign up (free)
# 2. Connect your GitHub account
# 3. When ready, deploy the repo with Root Directory: ./frontend
# 4. Set environment variable: NEXT_PUBLIC_API_URL=<your-render-url>
```

---

## Phase 3: Update Application Code

### Step 3.1: Update Backend

**File:** `backend/app/core/config.py`
```python
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://user:password@localhost/ipm"
    
    # Vector DB
    pinecone_api_key: str = ""
    pinecone_environment: str = "us-east1-gcp"
    
    # Storage
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_s3_bucket: str = "ipm-storage"
    aws_region: str = "us-east-1"
    
    # LLM
    llm_provider: str = "groq"
    groq_api_key: str = ""
    embedding_provider: str = "sentence-transformers"
    
    # API
    api_title: str = "IPM API"
    api_version: str = "1.0.0"
    api_description: str = "Intelligent Project Management API"
    
    # Environment
    environment: str = "development"
    debug: bool = False
    
    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()
```

### Step 3.2: Update Frontend

**File:** `frontend/next.config.js`
```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  },
  experimental: {
    isrMemoryCacheSize: 52 * 1024 * 1024, // 52mb
  },
  compress: true,
  poweredByHeader: false,
  productionBrowserSourceMaps: false, // Save memory
  swcMinify: true,
  // Optimize images
  images: {
    unoptimized: process.env.NEXT_PUBLIC_API_URL ? false : true,
  },
}

module.exports = nextConfig
```

---

## Phase 4: Deployment Instructions

### Step 4.1: Prepare Repository

```bash
# Add deployment files to git
git add .env.example render.yaml vercel.json
git add backend/Dockerfile frontend/Dockerfile
git commit -m "chore: prepare for cloud deployment"
git push origin main
```

### Step 4.2: Deploy Backend (Render)

```bash
# 1. Push to GitHub
git push origin main

# 2. In Render dashboard:
# - Click "New" → "Web Service"
# - Connect GitHub repo
# - Select "ipm-v0"
# - Set deployment settings (see Step 3.3)
# - Add environment variables:
DATABASE_URL=<from Supabase>
PINECONE_API_KEY=<from Pinecone>
AWS_ACCESS_KEY_ID=<from AWS>
AWS_SECRET_ACCESS_KEY=<from AWS>
AWS_S3_BUCKET=ipm-storage
GROQ_API_KEY=<your key>
LANGFUSE_PUBLIC_KEY=<your key>
LANGFUSE_SECRET_KEY=<your key>

# 3. Deploy
# 4. Note the Render URL (e.g., https://ipm-api.onrender.com)
```

### Step 4.3: Deploy Frontend (Vercel)

```bash
# 1. In Vercel dashboard:
# - Click "Add New" → "Project"
# - Import GitHub repository
# - Framework: Next.js
# - Root Directory: ./frontend
# - Build Command: npm run build
# - Output Directory: .next
# - Environment Variables:
NEXT_PUBLIC_API_URL=https://ipm-api.onrender.com

# 2. Deploy
# 3. Note Vercel URL (e.g., https://ipm.vercel.app)
```

### Step 4.4: Verify Deployment

```bash
# Test API health
curl https://ipm-api.onrender.com/health

# Test frontend
# Visit https://ipm.vercel.app in browser

# Check logs
# Render: Dashboard → ipm-api → Logs
# Vercel: Dashboard → ipm → Deployments → Logs
```

---

## 📊 Free Tier Limits & Costs

| Service | Free Tier | Limits | Cost If Exceeded |
|---------|-----------|--------|-----------------|
| **Neon DB** | 3 projects, 0.5 GB | Unlimited queries | $0.16/GB for extra storage |
| **Pinecone** | 1 pod | 1M vectors | $0.10 per 1M vectors/mo |
| **Render** | 512MB RAM | Auto-sleep after 15min inactivity | $7/month for always-on |
| **Vercel** | Unlimited | 100GB bandwidth/month | $0.50/GB |
| **Groq API** | Free | Rate limited | Commercial pricing |
| **Langfuse** | Free | 10M events/month | $20/month for more |
| **Total Monthly** | **$0** | See notes | Typically $10-30 |

---

## ⚠️ Important Considerations

### AWS S3 (File Storage) — Optional
- **Not included in your stack.** S3 was for storing files/documents in the cloud, but your app doesn't use it yet.
- **Local MinIO is still available** for development with `docker-compose`.
- If you need file storage later, you can add S3 (AWS free tier: 5GB/year).

### Cold Start Issues
- **Render free tier:** Services auto-sleep. First request takes 30-60 seconds.
- **Solution:** Use "Always On" ($7/month) or keep pinging the service.

### Rate Limits
- **Groq API:** Free tier is rate-limited (check their docs)
- **Pinecone:** Free tier limited to 1 pod
- **Render:** 10,000 requests/hour for free tier

### Data Persistence
- **Render:** No persistent storage on free tier
- **Solution:** Use database for all data, not ephemeral volumes

### Performance
- **Limited CPU:** 0.5 vCPU on Render (slow ML operations)
- **Solution:** Consider reducing model size or using API-based embeddings

---

## 🔧 Optional: Use API-Based Embeddings (Faster)

For better free tier performance:

```bash
# Install Groq embeddings (if available)
# Or use Hugging Face Inference API (free)

pip install huggingface-hub
```

```python
# backend/core/embedding_client.py - Alternative
from huggingface_hub import InferenceClient

hf_client = InferenceClient(
    api_key=os.getenv("HUGGINGFACE_API_KEY")
)

async def get_embedding(text: str):
    response = await asyncio.to_thread(
        hf_client.feature_extraction,
        text,
        model="sentence-transformers/all-MiniLM-L6-v2"
    )
    return response
```

---

## 📚 Troubleshooting

### Backend won't start
```bash
# Check logs in Render
# Common issues:
# 1. Missing DATABASE_URL → Add to env vars
# 2. Migration failed → Run locally first, check migrations
# 3. Import errors → Missing packages in requirements.txt
```

### Frontend can't reach API
```bash
# 1. Check NEXT_PUBLIC_API_URL in Vercel env vars
# 2. Check CORS on backend (app/main.py)
# 3. Ensure backend is running (not in sleep mode)
```

### Database connection issues
```bash
# 1. Test connection string locally:
psql "your-connection-string"

# 2. Whitelist your IP in Supabase
# 3. Ensure pool size is small (free tier limitation)
```

---

## ✅ Migration Checklist

- [ ] Create `.env.example` files ✓
- [ ] Update Dockerfiles for production ✓
- [ ] Add `render.yaml` for Render deployment ✓
- [ ] Add `vercel.json` for Vercel deployment ✓
- [ ] Create Neon database and copy connection string
- [ ] Create Pinecone account and API key
- [ ] Create Render account and link GitHub
- [ ] Create Vercel account and link GitHub
- [ ] Set up Render env vars (DATABASE_URL, PINECONE_API_KEY, GROQ_API_KEY, CORS_ORIGINS)
- [ ] Set up Vercel env vars (NEXT_PUBLIC_API_URL)
- [ ] Push code to GitHub
- [ ] Deploy backend on Render
- [ ] Deploy frontend on Vercel
- [ ] Test end-to-end functionality
- [ ] Update CORS_ORIGINS and NEXT_PUBLIC_API_URL after deployments

---

## 📖 Helpful Resources

- **Supabase:** https://supabase.com/docs
- **Pinecone:** https://docs.pinecone.io
- **AWS S3:** https://docs.aws.amazon.com/s3/
- **Render:** https://render.com/docs
- **Vercel:** https://vercel.com/docs
- **FastAPI Deployment:** https://fastapi.tiangolo.com/deployment/
- **Next.js Deployment:** https://nextjs.org/docs/deployment

---

## 🎯 Summary

**Your migration path:**
1. **Today:** Prepare code (env files, Dockerfiles, dependencies)
2. **Day 1:** Set up cloud accounts and databases
3. **Day 2:** Update backend code and deploy to Render
4. **Day 3:** Deploy frontend to Vercel and test
5. **Day 4:** Monitor and optimize

**Estimated time:** 4-6 hours for first deployment

**Total cost with free tier:** $0 (will scale to $20-50/month as usage grows)
