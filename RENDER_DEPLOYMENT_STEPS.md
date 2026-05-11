# Render Deployment Steps

## Step 1: Create Pinecone Index (Required First)

1. Go to https://pinecone.io dashboard
2. Click **Create Index**
3. Fill in:
   - **Name:** `ipm-vectors`
   - **Dimension:** `384`
   - **Metric:** `cosine`
4. Wait for creation (takes 1-2 minutes)
5. Note your **environment region** (appears in dashboard, e.g., `us-east1-gcp`)
6. Tell me the region so I can update the .env

---

## Step 2: Deploy Backend on Render

1. Go to https://render.com/dashboard
2. Click **New** → **Web Service**
3. Connect your GitHub repository (select the repo)
4. Configure:
   - **Name:** `ipm-api`
   - **Environment:** Python 3.11
   - **Build Command:** `pip install -r requirements.txt && alembic upgrade head`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Root Directory:** `backend`
5. Click **Create Web Service** (it will start deploying)
6. Go to **Environment** tab and add these variables:

```
DATABASE_URL=<your Neon async SQLAlchemy URL, ending with ?sslmode=require if Neon provides it>

ENVIRONMENT=production
DEBUG=false
CORS_ORIGINS=http://localhost:3000,https://your-vercel-url.vercel.app

LLM_PROVIDER=groq
GROQ_API_KEY=[REDACTED]

EMBEDDING_PROVIDER=local

PINECONE_API_KEY=<your Pinecone API key>
PINECONE_INDEX=ipm-vectors
PINECONE_REGION=<your Pinecone index region, for example us-east-1>
PINECONE_CLOUD=aws
PINECONE_INDEX_DIMENSION=384
PINECONE_AUTO_CREATE_INDEX=false
PINECONE_SEED_CATALOG_ON_STARTUP=true

LANGFUSE_PUBLIC_KEY=<your Langfuse public key>
LANGFUSE_SECRET_KEY=<your Langfuse secret key>
LANGFUSE_HOST=https://cloud.langfuse.com
```

7. Wait for deployment to complete
8. Once live, note your **Render URL** (e.g., `https://ipm-api-xxxxx.onrender.com`)

If Render only shows a generic Python 3 runtime, add this environment variable before deploying:

```
PYTHON_VERSION=3.11.9
```

That avoids the `pydantic-core` source-build failure on the default runtime.

---

## Step 3: Deploy Frontend on Vercel

1. Go to https://vercel.com/dashboard
2. Click **Add New** → **Project**
3. Select your GitHub repository
4. Configure:
   - **Framework Preset:** Next.js
   - **Root Directory:** `./frontend`
   - **Build Command:** `npm run build`
5. Add environment variable:
   - **Name:** `NEXT_PUBLIC_API_URL`
   - **Value:** `https://ipm-api-xxxxx.onrender.com` (your Render URL)
6. Click **Deploy**
7. Wait for deployment to complete
8. Note your **Vercel URL** (e.g., `https://ipm-xxxxx.vercel.app`)

If you change `NEXT_PUBLIC_API_URL` later, trigger a new Vercel redeploy so the
frontend bundle picks up the updated backend URL. The app will otherwise keep
using the value baked into the previous build.

---

## Step 4: Update CORS

1. Go back to Render dashboard → ipm-api → Environment
2. Update `CORS_ORIGINS` to:
   ```
   http://localhost:3000,https://ipm-xxxxx.vercel.app
   ```
   (replace `ipm-xxxxx` with your actual Vercel URL)
3. Click **Save**
4. Service will redeploy automatically

---

## Step 5: Verify Deployment

```bash
# Test backend health
curl https://ipm-api-xxxxx.onrender.com/health

# Visit frontend in browser
https://ipm-xxxxx.vercel.app
```

---

## Next Steps

- Give me your **Pinecone environment region** to finalize the setup
- Once both deployments are live, test creating a business need
- Monitor logs in Render/Vercel dashboards for errors
