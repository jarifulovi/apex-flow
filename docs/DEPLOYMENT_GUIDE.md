# ApexFlow Production Deployment Guide (`docs/DEPLOYMENT_GUIDE.md`)

> **Step-by-Step Guide for Deploying ApexFlow to Render (Backend), Vercel (Dashboard), and Docker Compose (VPS / Self-Hosted).**

---

## 📌 Architecture Overview & Deployment Topology

ApexFlow is architected with clear decoupling between the **Zero-Knowledge Backend Control Plane** and the **Next.js Observability Dashboard**:

```text
                               ┌──────────────────────────────────────────────┐
                               │           Vercel (Global Edge CDN)           │
                               │                                              │
                               │    ApexFlow Dashboard UI (Next.js 14)        │
                               │    (https://apexflow-dashboard.vercel.app)   │
                               └──────────────────────┬───────────────────────┘
                                                      │
                                                      │  (HTTPS / REST / WS)
                                                      ▼
 ┌───────────────────────────┐         ┌──────────────────────────────────────┐
 │ Developer Worker SDKs     │         │      Render (Web Service Container)  │
 │                           │         │                                      │
 │ - Local Dev / Cloud VMs   ├────────►│  ApexFlow Control Plane (FastAPI)    │
 │ - Python / TS / Go Workers│ (HTTPS) │  (https://apexflow-api.onrender.com) │
 └───────────────────────────┘         └──────────┬──────────────────┬────────┘
                                                  │                  │
                                                  ▼                  ▼
                                       ┌──────────────────┐  ┌────────────────┐
                                       │ Managed Postgres │  │ Cloud Storage  │
                                       │ (Render/Supabase)│  │ (S3 / R2 / disk│
                                       └──────────────────┘  └────────────────┘
```

---

## 🚀 Option A: Cloud Deployment (Render + Vercel)

### Part 1: Deploy Backend Control Plane on Render

1. **Log in to Render**:
   - Go to [Render Dashboard](https://dashboard.render.com) and log in.

2. **Create Web Service**:
   - Click **New +** $\rightarrow$ **Web Service**.
   - Connect your GitHub repository (`apex-flow`).
   - Set **Root Directory**: `apex-flow-backend`.
   - Set **Runtime**: `Docker`.
   - Set **Dockerfile Path**: `./Dockerfile`.
   - Choose instance plan (**Starter** or **Standard**).

3. **Configure Health Check**:
   - Under **Advanced Settings**, set **Health Check Path**: `/api/v1/health`.

4. **Set Environment Variables**:
   Add the following variables in the Render Dashboard:

   | Environment Variable | Recommended Value / Source | Description |
   | :--- | :--- | :--- |
   | `DATABASE_URL` | `postgresql+asyncpg://...` | Connection string for Render Postgres or Supabase DB. |
   | `PROJECT_NAME` | `ApexFlow Control Plane` | Display name for API docs. |
   | `BACKEND_CORS_ORIGINS` | `https://<your-vercel-dashboard-app>.vercel.app` | Allowed CORS origins for dashboard cross-origin calls. |
   | `STORAGE_PROVIDER` | `local` (or `s3`) | Storage adapter provider. |
   | `PAYLOAD_MAX_INLINE_BYTES` | `262144` | 250KB offload threshold. |
   | `SUPABASE_JWT_SECRET` | `<your-supabase-jwt-secret>` | Secret key for verifying dashboard Bearer tokens. |
   | `S3_BUCKET_NAME` | `<your-s3-bucket-name>` | *(Optional)* Target S3/R2 bucket name. |
   | `S3_ENDPOINT_URL` | `<your-r2-endpoint-url>` | *(Optional)* Endpoint URL for R2/MinIO. |
   | `AWS_ACCESS_KEY_ID` | `<access-key-id>` | *(Optional)* Cloud storage access key ID. |
   | `AWS_SECRET_ACCESS_KEY` | `<secret-key>` | *(Optional)* Cloud storage secret access key. |

5. **Deploy & Verify**:
   - Click **Create Web Service**.
   - Once deployed, test the health check endpoint:
     ```bash
     curl https://<your-render-backend-app>.onrender.com/api/v1/health
     # Returns: {"status":"healthy","service":"ApexFlow Control Plane"}
     ```

---

### Part 2: Deploy Observability Dashboard on Vercel

1. **Log in to Vercel**:
   - Go to [Vercel Dashboard](https://vercel.com/dashboard) and log in.

2. **Import Repository**:
   - Click **Add New...** $\rightarrow$ **Project**.
   - Import your GitHub repository (`apex-flow`).

3. **Configure Framework & Root Directory**:
   - Set **Framework Preset**: `Next.js`.
   - Set **Root Directory**: `apex-flow-dashboard`.

4. **Set Environment Variables**:
   Add the following environment variables in Vercel:

   | Environment Variable | Value | Description |
   | :--- | :--- | :--- |
   | `NEXT_PUBLIC_API_URL` | `https://<your-render-backend-app>.onrender.com` | Deployed Render API URL. |
   | `NEXT_PUBLIC_SUPABASE_URL` | `https://<your-project-ref>.supabase.co` | Supabase Project URL. |
   | `NEXT_PUBLIC_SUPABASE_ANON_KEY` | `<your-supabase-anon-key>` | Supabase Anonymous Public Key. |

5. **Deploy**:
   - Click **Deploy**. Vercel will build and deploy the Next.js standalone frontend.
   - Open your deployed Vercel domain in browser (e.g. `https://apexflow-dashboard.vercel.app`).

---

## 🐳 Option B: Self-Hosted Docker Compose (VPS Deployment)

For single-server deployment on **DigitalOcean Droplet**, **AWS EC2**, **Hetzner**, or **Linode**:

### 1. SSH into VPS & Clone Repository
```bash
git clone https://github.com/<your-org>/apex-flow.git
cd apex-flow
```

### 2. Configure Production Environment Variables
```bash
cp .env.production.template .env
```
Edit `.env` and configure your production credentials:
```bash
nano .env
```

### 3. Build & Start Multi-Container Stack
```bash
docker compose up -d --build
```

### 4. Verify Running Services
```bash
docker compose ps
```
Output will confirm:
- `apexflow-postgres` running on port `5432` (healthy)
- `apexflow-backend` running on port `8000` (healthy)
- `apexflow-dashboard` running on port `3000`

---

## 🔒 Security & Post-Deployment Checklist

- [ ] **HTTPS/TLS**: Ensure backend and dashboard URLs use `https://`.
- [ ] **CORS Configuration**: Verify FastAPI CORS middleware allows dashboard origin.
- [ ] **API Keys**: Generate production project API keys via the dashboard UI or `/api/v1/keys` endpoint.
- [ ] **SDK Configuration**: Update worker SDK configuration to point to production backend:
  ```python
  from apex_flow_sdk import ApexFlowClient

  client = ApexFlowClient(
      base_url="https://apexflow-api.onrender.com",
      project_key="af_live_your_production_api_key_here"
  )
  ```
