# Production Deployment Guide

> Deploy LenQuant Website Fabric to AWS EC2 with Docker, Nginx, and Let's Encrypt.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Domain & DNS Configuration](#domain--dns-configuration)
4. [AWS S3 Setup (Asset Storage)](#aws-s3-setup-asset-storage)
5. [Amazon Bedrock Setup (LLM)](#amazon-bedrock-setup-llm)
6. [Docker Configuration](#docker-configuration)
7. [Nginx & SSL Configuration](#nginx--ssl-configuration)
8. [Environment Configuration](#environment-configuration)
9. [EC2 Instance Setup](#ec2-instance-setup)
10. [Deployment Procedure](#deployment-procedure)
11. [MongoDB Atlas VPC Peering](#mongodb-atlas-vpc-peering)
12. [Monitoring & Logs](#monitoring--logs)
13. [Backup & Recovery](#backup--recovery)
14. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

```
                         ┌─────────────────────────────────────────────┐
                         │              EC2 Instance                    │
                         │                                             │
Internet ──► Nginx:443 ──┤──► Next.js :3000  (sites.lenquant.com)     │
             (SSL term)  │      ├── /         Landing page (TBD)       │
                         │      ├── /nsa/*    Operator dashboard       │
                         │      └── /st/*     Generated sites (SSR)    │
                         │                                             │
                         │──► FastAPI :8000  (sites-api.lenquant.com)  │
                         │      └── /api/v1/* All API endpoints        │
                         │                                             │
                         │──► Redis :6379     (internal only)           │
                         │──► Celery Worker   (background jobs)         │
                         └─────────────────────────────────────────────┘
                                        │           │
                                        ▼           ▼
                               MongoDB Atlas    AWS S3 (assets)
                                                Amazon Bedrock (LLM)
```

### Domain Routing

| Domain | Target | Purpose |
|--------|--------|---------|
| `sites.lenquant.com` | Next.js app (port 3000) | Landing page + operator dashboard |
| `sites-api.lenquant.com` | FastAPI (port 8000) | REST API |
| `sites.lenquant.com/st/{slug}` | Next.js SSR | Public generated sites |

### Technology Stack Changes from Local

| Component | Local | Production |
|-----------|-------|------------|
| LLM | Google Gemini | Amazon Bedrock (Claude Sonnet 4.6) |
| Asset Storage | Local filesystem / GCP | AWS S3 |
| Reverse Proxy | None | Nginx + Let's Encrypt |
| Process Management | Manual | Docker Compose |
| SSL | None | Let's Encrypt (auto-renew) |

---

## Prerequisites

### AWS Account Requirements

- EC2 access (minimum `t3.medium` recommended — 2 vCPU, 4GB RAM)
- S3 full access for asset bucket
- Bedrock model access enabled for `us.anthropic.claude-sonnet-4-6-v1` in your region
- IAM user or role with programmatic access
- Security group allowing ports 80, 443, and 22 (SSH)

### Software on EC2

- Ubuntu 22.04 LTS (or Amazon Linux 2023)
- Docker Engine 24+
- Docker Compose v2
- Git
- Certbot (for Let's Encrypt)

### External Services

- MongoDB Atlas cluster (existing) — whitelist EC2 IP or set up VPC peering
- Domain DNS access for `lenquant.com`
- AWS S3 bucket created
- Amazon Bedrock model access approved

---

## Domain & DNS Configuration

### DNS Records

Add these records at your DNS provider (Route 53 or external):

```
Type    Name                    Value                   TTL
A       sites.lenquant.com      <EC2-PUBLIC-IP>         300
A       sites-api.lenquant.com  <EC2-PUBLIC-IP>         300
```

If using an Elastic IP (recommended for stability):

```bash
# Allocate and associate Elastic IP
aws ec2 allocate-address --domain vpc
aws ec2 associate-address --instance-id <INSTANCE_ID> --allocation-id <ALLOC_ID>
```

### Verify DNS Propagation

```bash
dig sites.lenquant.com +short
dig sites-api.lenquant.com +short
```

Both should return your EC2 public/Elastic IP.

---

## AWS S3 Setup (Asset Storage)

### Create the Bucket

```bash
aws s3 mb s3://lenquant-site-assets --region us-east-1
```

### Bucket Policy (public read for generated site assets)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadAssets",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::lenquant-site-assets/public/*"
    }
  ]
}
```

### IAM Policy for the Application

Create an IAM user (`lenquant-app`) or use an instance profile with this policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::lenquant-site-assets",
        "arn:aws:s3:::lenquant-site-assets/*"
      ]
    }
  ]
}
```

### CORS Configuration (for browser uploads if needed)

```json
[
  {
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["GET", "PUT"],
    "AllowedOrigins": ["https://sites.lenquant.com"],
    "ExposeHeaders": ["ETag"],
    "MaxAgeSeconds": 3600
  }
]
```

---

## Amazon Bedrock Setup (LLM)

### Enable Model Access

1. Go to **Amazon Bedrock** → **Model access** in AWS Console
2. Request access to `Anthropic Claude Sonnet 4.6` (`us.anthropic.claude-sonnet-4-6-v1`)
3. Wait for approval (usually instant for Anthropic models)

### IAM Policy for Bedrock

Add to the application IAM user/role:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": "arn:aws:bedrock:us-east-1::foundation-model/us.anthropic.claude-sonnet-4-6-v1"
    }
  ]
}
```

### Region Consideration

Bedrock model availability varies by region. Claude Sonnet 4.6 is available in `us-east-1` and `us-west-2`. Choose your EC2 region accordingly, or use cross-region inference.

### Code Changes Required

The backend currently uses `google-genai` (Gemini). This must be replaced with `boto3` Bedrock calls. The integration points are:

| File | Current (Gemini) | New (Bedrock) |
|------|-------------------|---------------|
| `apps/backend/app/core/gemini_client.py` | Gemini API wrapper | Replace with Bedrock client |
| `apps/backend/app/core/sites.py` | Calls Gemini for site generation | Update to use Bedrock |
| `apps/backend/app/core/visual_redesign.py` | Gemini Vision for QA | Update to use Bedrock multimodal |
| `apps/backend/app/core/screenshot_analyzer.py` | Gemini Vision scoring | Update to use Bedrock multimodal |
| `apps/backend/app/core/extraction.py` | Gemini for brief generation | Update to use Bedrock |

Example Bedrock invocation (replacing Gemini calls):

```python
import boto3
import json

bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")

def invoke_claude(prompt: str, system: str = "", max_tokens: int = 4096) -> str:
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": prompt}]
    })
    response = bedrock.invoke_model(
        modelId="us.anthropic.claude-sonnet-4-6-v1",
        contentType="application/json",
        accept="application/json",
        body=body
    )
    result = json.loads(response["body"].read())
    return result["content"][0]["text"]


def invoke_claude_vision(prompt: str, image_bytes: bytes, media_type: str = "image/png") -> str:
    import base64
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 4096,
        "messages": [{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": base64.b64encode(image_bytes).decode()
                    }
                },
                {"type": "text", "text": prompt}
            ]
        }]
    })
    response = bedrock.invoke_model(
        modelId="us.anthropic.claude-sonnet-4-6-v1",
        contentType="application/json",
        accept="application/json",
        body=body
    )
    result = json.loads(response["body"].read())
    return result["content"][0]["text"]
```

---

## Docker Configuration

### Project File Structure

```
LenManag/
├── docker-compose.yml          # Orchestrates all services
├── apps/
│   ├── backend/
│   │   └── Dockerfile          # FastAPI + Celery worker
│   └── web/
│       └── Dockerfile          # Next.js standalone
├── nginx/
│   ├── nginx.conf              # Main nginx config
│   └── conf.d/
│       └── default.conf        # Site-specific server blocks
└── .env.production             # Production environment vars
```

### `apps/backend/Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# System dependencies for Playwright and general build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[dev]"

# Install Playwright browsers (for screenshot QA)
RUN playwright install chromium --with-deps

# Copy application code
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

### `apps/web/Dockerfile`

```dockerfile
FROM node:20-alpine AS base

# Install dependencies
FROM base AS deps
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN corepack enable pnpm && pnpm install --frozen-lockfile

# Build the application
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

ARG NEXT_PUBLIC_API_BASE_URL
ARG NEXT_PUBLIC_APP_URL
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL
ENV NEXT_PUBLIC_APP_URL=$NEXT_PUBLIC_APP_URL

RUN corepack enable pnpm && pnpm run build

# Production runner
FROM base AS runner
WORKDIR /app
ENV NODE_ENV=production

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
```

### `docker-compose.yml`

```yaml
services:
  redis:
    image: redis:7-alpine
    restart: unless-stopped
    ports:
      - "127.0.0.1:6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3

  backend:
    build:
      context: ./apps/backend
      dockerfile: Dockerfile
    restart: unless-stopped
    ports:
      - "127.0.0.1:8000:8000"
    env_file:
      - .env.production
    depends_on:
      redis:
        condition: service_healthy
    volumes:
      - backend_tmp:/app/tmp
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  celery-worker:
    build:
      context: ./apps/backend
      dockerfile: Dockerfile
    restart: unless-stopped
    command: celery -A app.core.celery_app worker --loglevel=info --concurrency=2
    env_file:
      - .env.production
    depends_on:
      redis:
        condition: service_healthy
      backend:
        condition: service_healthy
    volumes:
      - backend_tmp:/app/tmp

  celery-beat:
    build:
      context: ./apps/backend
      dockerfile: Dockerfile
    restart: unless-stopped
    command: celery -A app.core.celery_app beat --loglevel=info
    env_file:
      - .env.production
    depends_on:
      redis:
        condition: service_healthy

  web:
    build:
      context: ./apps/web
      dockerfile: Dockerfile
      args:
        NEXT_PUBLIC_API_BASE_URL: https://sites-api.lenquant.com
        NEXT_PUBLIC_APP_URL: https://sites.lenquant.com
    restart: unless-stopped
    ports:
      - "127.0.0.1:3000:3000"
    env_file:
      - .env.production
    depends_on:
      backend:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:3000"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  redis_data:
  backend_tmp:
```

---

## Nginx & SSL Configuration

### Install Nginx & Certbot on EC2

```bash
sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx
```

### `nginx/conf.d/default.conf`

Initial HTTP-only config (before SSL):

```nginx
# Redirect HTTP to HTTPS (enabled after certbot runs)
server {
    listen 80;
    server_name sites.lenquant.com sites-api.lenquant.com;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}

# Frontend: sites.lenquant.com
server {
    listen 443 ssl;
    server_name sites.lenquant.com;

    ssl_certificate /etc/letsencrypt/live/sites.lenquant.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/sites.lenquant.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Next.js app
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    # Static assets caching
    location /_next/static/ {
        proxy_pass http://127.0.0.1:3000;
        expires 365d;
        add_header Cache-Control "public, immutable";
    }
}

# Backend API: sites-api.lenquant.com
server {
    listen 443 ssl;
    server_name sites-api.lenquant.com;

    ssl_certificate /etc/letsencrypt/live/sites-api.lenquant.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/sites-api.lenquant.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security headers
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Request size limit (for image uploads)
    client_max_body_size 20M;

    # FastAPI backend
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeout for long-running generation requests
        proxy_read_timeout 300s;
        proxy_connect_timeout 10s;
    }
}
```

### Obtain SSL Certificates

```bash
# Stop nginx temporarily (or use webroot method)
sudo certbot certonly --nginx \
  -d sites.lenquant.com \
  -d sites-api.lenquant.com \
  --email your-email@lenquant.com \
  --agree-tos \
  --non-interactive

# Verify auto-renewal
sudo certbot renew --dry-run
```

### Auto-Renewal Cron

Certbot installs a systemd timer by default. Verify:

```bash
sudo systemctl status certbot.timer
```

If not present, add a cron:

```bash
echo "0 3 * * * certbot renew --quiet --post-hook 'systemctl reload nginx'" | sudo tee /etc/cron.d/certbot-renew
```

---

## Environment Configuration

### `.env.production`

```bash
# ─── MongoDB ───────────────────────────────────────────────────────
MONGODB_URI=mongodb+srv://<user>:<password>@lenmanag.zzbkrv.mongodb.net/
MONGODB_DB_NAME=lenquant

# ─── Authentication ───────────────────────────────────────────────
SESSION_SECRET=<generate-with: openssl rand -hex 32>
AUTH_ALLOWLIST_EMAILS=operator1@lenquant.com,operator2@lenquant.com
AUTH_ALLOWLIST_DOMAINS=lenquant.com
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_SAMESITE=lax
SESSION_COOKIE_DOMAIN=.lenquant.com
SESSION_COOKIE_MAX_AGE_SECONDS=86400

# ─── Application URLs ─────────────────────────────────────────────
NEXT_PUBLIC_API_BASE_URL=https://sites-api.lenquant.com
NEXT_PUBLIC_APP_URL=https://sites.lenquant.com
BACKEND_CORS_ORIGINS=https://sites.lenquant.com
PREVIEW_BASE_URL=https://sites.lenquant.com/st

# ─── Celery / Redis ───────────────────────────────────────────────
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_TASK_ALWAYS_EAGER=false

# ─── AWS Credentials ──────────────────────────────────────────────
AWS_ACCESS_KEY_ID=<your-access-key>
AWS_SECRET_ACCESS_KEY=<your-secret-key>
AWS_DEFAULT_REGION=us-east-1

# ─── S3 Asset Storage ─────────────────────────────────────────────
ASSET_STORAGE_BACKEND=s3
ASSET_DOWNLOAD_ENABLED=true
ASSET_S3_BUCKET=lenquant-site-assets
ASSET_S3_REGION=us-east-1
ASSET_S3_PREFIX=public/

# ─── Amazon Bedrock (LLM) ─────────────────────────────────────────
LLM_PROVIDER=bedrock
BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-6-v1
BEDROCK_REGION=us-east-1
# Max tokens for generation calls
BEDROCK_MAX_TOKENS=4096

# ─── Visual Redesign (Screenshot QA) ──────────────────────────────
VISUAL_REDESIGN_ENABLED=true
VISUAL_REDESIGN_MAX_ITERATIONS=3
VISUAL_REDESIGN_QUALITY_THRESHOLD=7.5

# ─── Crawl Settings ───────────────────────────────────────────────
CRAWL_MAX_PAGES=10
CRAWL_BUDGET_BYTES=3145728
CRAWL_TIME_LIMIT_SECONDS=60
```

### Key Differences from Local `.env`

| Variable | Local | Production |
|----------|-------|------------|
| `GEMINI_API_KEY` | Set | **Removed** (replaced by Bedrock) |
| `LLM_PROVIDER` | Not set (defaults to gemini) | `bedrock` |
| `BEDROCK_MODEL_ID` | Not set | `us.anthropic.claude-sonnet-4-6-v1` |
| `ASSET_STORAGE_BACKEND` | `local` | `s3` |
| `CELERY_TASK_ALWAYS_EAGER` | `true` | `false` |
| `SESSION_COOKIE_SECURE` | `false` | `true` |
| `BACKEND_CORS_ORIGINS` | `http://localhost:3000` | `https://sites.lenquant.com` |
| `CELERY_BROKER_URL` | Not set | `redis://redis:6379/0` |

---

## EC2 Instance Setup

### Launch Instance

**Recommended spec:**
- AMI: Ubuntu 22.04 LTS
- Instance type: `t3.medium` (2 vCPU, 4GB RAM) — scale to `t3.large` if handling many concurrent generations
- Storage: 30GB gp3 EBS
- Security Group: Allow inbound 22 (SSH), 80 (HTTP), 443 (HTTPS)
- Key pair: Create or use existing

### Initial Server Setup

```bash
# Connect to EC2
ssh -i your-key.pem ubuntu@<EC2-PUBLIC-IP>

# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER

# Install Docker Compose v2
sudo apt install -y docker-compose-plugin

# Install Nginx
sudo apt install -y nginx

# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Install Git
sudo apt install -y git

# Log out and back in for docker group to take effect
exit
```

### Clone the Repository

```bash
ssh -i your-key.pem ubuntu@<EC2-PUBLIC-IP>

cd /opt
sudo mkdir lenquant && sudo chown ubuntu:ubuntu lenquant
git clone <YOUR_REPO_URL> /opt/lenquant
cd /opt/lenquant
```

### Security Group Rules

| Type | Protocol | Port | Source | Purpose |
|------|----------|------|--------|---------|
| SSH | TCP | 22 | Your IP / bastion | Admin access |
| HTTP | TCP | 80 | 0.0.0.0/0 | Redirect to HTTPS |
| HTTPS | TCP | 443 | 0.0.0.0/0 | Production traffic |

**Block all other inbound traffic.** Redis (6379), backend (8000), and frontend (3000) are internal only (bound to 127.0.0.1 in docker-compose).

---

## Deployment Procedure

### First-Time Deployment

```bash
cd /opt/lenquant

# 1. Create production env file
cp .env.example .env.production
nano .env.production  # Fill in all production values (see Environment Configuration)

# 2. Build and start Docker containers
docker compose build
docker compose up -d

# 3. Verify containers are running
docker compose ps
docker compose logs --tail=50

# 4. Configure Nginx
sudo cp nginx/conf.d/default.conf /etc/nginx/sites-available/lenquant
sudo ln -s /etc/nginx/sites-available/lenquant /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx

# 5. Obtain SSL certificates (DNS must be pointing to this server first)
sudo certbot --nginx -d sites.lenquant.com -d sites-api.lenquant.com

# 6. Verify everything works
curl -I https://sites.lenquant.com
curl -I https://sites-api.lenquant.com/api/v1/health
```

### Updating the Application

```bash
cd /opt/lenquant

# Pull latest code
git pull origin main

# Rebuild and restart (zero-downtime with rolling restart)
docker compose build
docker compose up -d --force-recreate

# Verify health
docker compose ps
curl -s https://sites-api.lenquant.com/api/v1/health | jq .
```

### Rollback

```bash
cd /opt/lenquant

# Rollback to previous commit
git log --oneline -5  # Find the commit to roll back to
git checkout <commit-hash>

# Rebuild
docker compose build
docker compose up -d --force-recreate
```

---

## GitHub Actions CI/CD Setup

Step-by-step guide to configure automated deployment from GitHub to EC2.

### Overview

When you push to `main`, the pipeline runs: **test → lint-web → docker-build → deploy**. The deploy job SSHs into your EC2 instance, pulls the code, rebuilds Docker images, and restarts services.

---

### Step 1: Generate an SSH Key Pair for GitHub Actions

On your local machine, generate a dedicated deploy key (do NOT reuse your personal `lenquant.pem`):

```bash
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/github_deploy_lenquant -N ""
```

This creates two files:
- `~/.ssh/github_deploy_lenquant` — private key (goes to GitHub Secrets)
- `~/.ssh/github_deploy_lenquant.pub` — public key (goes to the EC2 server)

---

### Step 2: Add the Public Key to the EC2 Server

SSH into your EC2 instance using your existing key:

```bash
ssh -i C:\Users\smikl\.ssh\lenquant.pem ubuntu@ec2-32-194-123-142.compute-1.amazonaws.com
```

Then add the deploy public key to authorized_keys:

```bash
# On the EC2 server:
echo "ssh-ed25519 AAAA...your-public-key-content... github-actions-deploy" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

(Copy the content of `~/.ssh/github_deploy_lenquant.pub` from your local machine.)

Verify it works from your machine:

```bash
ssh -i ~/.ssh/github_deploy_lenquant ubuntu@ec2-32-194-123-142.compute-1.amazonaws.com "echo OK"
```

---

### Step 3: Configure GitHub Repository Secrets

Go to your GitHub repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**.

Add these 3 secrets:

| Secret Name | Value | How to Get It |
|-------------|-------|---------------|
| `EC2_SSH_KEY` | Contents of `~/.ssh/github_deploy_lenquant` (the private key) | `cat ~/.ssh/github_deploy_lenquant` — copy the entire output including `-----BEGIN` and `-----END` lines |
| `EC2_HOST` | `ec2-32-194-123-142.compute-1.amazonaws.com` | Your EC2 public DNS |
| `EC2_USER` | `ubuntu` | The SSH username for Ubuntu AMI |

To copy the private key on Windows:

```powershell
Get-Content C:\Users\smikl\.ssh\github_deploy_lenquant | Set-Clipboard
```

Or in Git Bash:

```bash
cat ~/.ssh/github_deploy_lenquant | clip
```

---

### Step 4: Create the GitHub Environment

Go to your GitHub repo → **Settings** → **Environments** → **New environment**.

1. Name it: `production`
2. (Optional) Add protection rules:
   - **Required reviewers** — if you want manual approval before each deploy
   - **Wait timer** — add a delay if you want time to cancel
3. Click **Save protection rules**

The `deploy` job in CI references `environment: production`, which gates it behind this environment.

---

### Step 5: Prepare the EC2 Server

SSH into EC2 and ensure the repo is cloned and Docker is ready:

```bash
ssh -i C:\Users\smikl\.ssh\lenquant.pem ubuntu@ec2-32-194-123-142.compute-1.amazonaws.com
```

```bash
# Clone the repo (first time only)
sudo mkdir -p /opt/lenquant
sudo chown ubuntu:ubuntu /opt/lenquant
git clone https://github.com/guerra2fernando/LenManag.git /opt/lenquant
cd /opt/lenquant

# Verify Docker is installed and running
docker --version
docker compose version

# If not installed:
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
sudo apt install -y docker-compose-plugin
# Log out and back in for group to take effect

# Create the production env file
cp .env.example .env.production
nano .env.production  # Fill in real production values
```

Make sure git can pull without prompting for credentials. If the repo is private, configure a deploy token:

```bash
# Option A: GitHub deploy token (read-only, recommended)
# Go to GitHub repo → Settings → Deploy keys → Add deploy key
# Paste the EC2 server's SSH public key
ssh-keygen -t ed25519 -C "ec2-deploy" -f ~/.ssh/github_ec2 -N ""
cat ~/.ssh/github_ec2.pub
# Add this as a deploy key in GitHub

# Configure git to use it
echo -e "Host github.com\n  IdentityFile ~/.ssh/github_ec2\n  StrictHostKeyChecking no" >> ~/.ssh/config

# Set remote to SSH
cd /opt/lenquant
git remote set-url origin git@github.com:guerra2fernando/LenManag.git
git pull  # verify it works
```

---

### Step 6: Verify the Full Pipeline

1. Make a small change (e.g., edit a comment in any file)
2. Push to `main`:
   ```bash
   git add -A && git commit -m "test: trigger CI/CD pipeline" && git push
   ```
3. Go to GitHub → **Actions** tab → watch the workflow run
4. It should:
   - Run tests (Python lint + pytest)
   - Lint the frontend (eslint + tsc)
   - Build both Docker images
   - SSH into EC2, pull, rebuild, restart, health check

---

### Troubleshooting GitHub Actions Deploy

**"Permission denied (publickey)"**
- The private key in `EC2_SSH_KEY` doesn't match what's in `~/.ssh/authorized_keys` on EC2
- Make sure you copied the entire private key including header/footer lines
- Verify the public key is in EC2's `authorized_keys`

**"Host key verification failed"**
- The `appleboy/ssh-action` handles this automatically, but if it fails, SSH into the server manually once to accept the host key, or set `StrictHostKeyChecking no` in the action

**"docker compose: command not found"**
- Install Docker Compose v2 plugin on EC2: `sudo apt install docker-compose-plugin`

**"git pull fails"**
- If private repo: set up a deploy key (see Step 5)
- If public repo: ensure remote is `https://github.com/...`

**"health check fails after deploy"**
- Check logs: `ssh into EC2` → `cd /opt/lenquant && docker compose logs --tail=50 backend`
- Common cause: missing env var in `.env.production`

---

### Secrets Summary

| Where | What | Purpose |
|-------|------|---------|
| GitHub Secrets | `EC2_SSH_KEY` | Private key for SSH into EC2 |
| GitHub Secrets | `EC2_HOST` | `ec2-32-194-123-142.compute-1.amazonaws.com` |
| GitHub Secrets | `EC2_USER` | `ubuntu` |
| EC2 `~/.ssh/authorized_keys` | Deploy public key | Allows GitHub Actions to SSH in |
| EC2 `/opt/lenquant/.env.production` | All app env vars | App configuration (never in git) |
| GitHub repo (or EC2 `~/.ssh`) | Deploy key for git pull | Allows EC2 to pull private repo |

---

## MongoDB Atlas VPC Peering

For production security, use VPC peering instead of IP whitelisting.

### Option A: IP Whitelisting (Quick Start)

1. Go to MongoDB Atlas → Network Access
2. Add your EC2 Elastic IP to the IP Access List
3. Done — connection works immediately

### Option B: VPC Peering (Recommended for Production)

1. In Atlas → Network Access → Peering → Add Peering Connection
2. Select AWS, enter:
   - AWS Account ID
   - VPC ID
   - VPC CIDR
   - Region
3. Accept the peering request in AWS VPC Console
4. Update route tables in both VPCs
5. In Atlas, add the VPC CIDR to the IP Access List

After peering, update `MONGODB_URI` to use the private connection string (no `+srv`, uses internal DNS).

---

## Monitoring & Logs

### Docker Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f backend
docker compose logs -f celery-worker
docker compose logs -f web

# Last 100 lines
docker compose logs --tail=100 backend
```

### Health Checks

```bash
# API health
curl https://sites-api.lenquant.com/api/v1/health

# Frontend health
curl -I https://sites.lenquant.com

# Redis
docker compose exec redis redis-cli ping

# Celery worker status
docker compose exec celery-worker celery -A app.core.celery_app inspect active
```

### Disk Space Monitoring

```bash
# Check disk usage
df -h

# Docker disk usage
docker system df

# Clean up unused images/containers
docker system prune -f
```

### Recommended: Set Up Log Rotation

```bash
# /etc/docker/daemon.json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

Then restart Docker: `sudo systemctl restart docker`

### Optional: CloudWatch Agent

For centralized logging and metrics, install the CloudWatch agent:

```bash
sudo apt install -y amazon-cloudwatch-agent
```

Configure to ship Docker logs and system metrics (CPU, memory, disk) to CloudWatch.

---

## Backup & Recovery

### MongoDB

MongoDB Atlas provides automated backups. Verify:
- Atlas → Cluster → Backup → Continuous Backup is enabled
- Set retention period (minimum 7 days recommended)

### S3 Assets

Enable versioning on the S3 bucket:

```bash
aws s3api put-bucket-versioning \
  --bucket lenquant-site-assets \
  --versioning-configuration Status=Enabled
```

### Application State

The application is stateless (all data in MongoDB + S3). Recovery is:
1. Launch new EC2 instance
2. Run deployment procedure
3. Point DNS to new instance

### Redis Data

Redis is used only as a message broker (Celery). No persistent data needs backup — jobs will re-queue on restart.

---

## Troubleshooting

### Container Won't Start

```bash
# Check logs for the failing container
docker compose logs backend

# Common issues:
# - Missing env vars → check .env.production
# - MongoDB connection failed → check MONGODB_URI and IP whitelist
# - Port already in use → check nothing else is on 8000/3000
```

### SSL Certificate Issues

```bash
# Check certificate status
sudo certbot certificates

# Force renewal
sudo certbot renew --force-renewal

# If certbot fails, ensure port 80 is open and DNS resolves correctly
```

### 502 Bad Gateway from Nginx

```bash
# Check if backend containers are running
docker compose ps

# Check if ports are listening
ss -tlnp | grep -E '3000|8000'

# Restart the failing service
docker compose restart backend
```

### Celery Jobs Not Processing

```bash
# Check worker status
docker compose logs celery-worker

# Check Redis connectivity
docker compose exec redis redis-cli ping

# Restart worker
docker compose restart celery-worker
```

### High Memory Usage

```bash
# Check per-container memory
docker stats --no-stream

# If backend OOM: reduce uvicorn workers or increase instance size
# If Celery OOM: reduce concurrency in docker-compose.yml
```

### MongoDB Connection Timeout

```bash
# Test connectivity from within container
docker compose exec backend python -c "
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
async def test():
    client = AsyncIOMotorClient('YOUR_URI', serverSelectionTimeoutMS=5000)
    await client.admin.command('ping')
    print('Connected!')
asyncio.run(test())
"
```

---

## Code Changes Checklist

### Backend Changes — DONE

- [x] **Created `apps/backend/app/core/bedrock_client.py`** — Bedrock wrapper (text + vision + batch + refinement)
- [x] **Created `apps/backend/app/core/llm.py`** — Provider abstraction (`get_llm_client()` routes by `LLM_PROVIDER`)
- [x] **Updated `apps/backend/app/core/config.py`** — Added `llm_provider`, `bedrock_*`, `asset_s3_region/prefix` settings
- [x] **Updated `apps/backend/app/core/sites.py`** — Switched to `get_llm_client()`
- [x] **`apps/backend/app/core/extraction.py`** — No change needed (fully rule-based, no LLM calls)
- [x] **Updated `apps/backend/app/core/visual_redesign.py`** — Switched to `get_llm_client()`
- [x] **Updated `apps/backend/app/core/screenshot_analyzer.py`** — Switched to `get_llm_client()`
- [x] **Created `apps/backend/app/core/asset_storage_s3.py`** — S3 storage backend (upload/delete/presigned URLs)
- [x] **Updated `apps/backend/app/core/asset_urls.py`** — Added S3 routing
- [x] **Updated `apps/backend/app/core/asset_downloader.py`** — Added S3 routing
- [x] **Updated `apps/backend/app/core/asset_retention.py`** — Added S3 purge support
- [x] **Updated `apps/backend/pyproject.toml`** — Cleaned deps, kept `google-genai` as optional
- [x] **Created `apps/backend/Dockerfile`**
- [x] **Created `apps/backend/.dockerignore`**

### Frontend Changes — DONE

- [x] **Fixed `apps/web/src/lib/constants.ts`** — Corrected fallback port from 8003 to 8000
- [x] **Created `apps/web/Dockerfile`** — Multi-stage build with standalone output
- [x] **Created `apps/web/.dockerignore`**

### Infrastructure Files — DONE

- [x] **Created `docker-compose.yml`** at project root (redis, backend, celery-worker, celery-beat, web)
- [x] **Created `nginx/conf.d/default.conf`** — SSL termination for both domains
- [x] **Updated `.env.example`** — Complete template with all production env vars
- [x] **Updated `.github/workflows/ci.yml`** — Added lint-web, docker-build, and deploy jobs

### Remaining (on EC2 at deploy time)

- [ ] `.env.production` (fill in real values from `.env.example` template)
- [ ] SSL certificates via certbot
- [ ] MongoDB Atlas IP whitelist / VPC peering

---

## Security Checklist

- [ ] No secrets in git (use `.env.production` on server only, not committed)
- [ ] MongoDB Atlas IP whitelist or VPC peering configured
- [ ] S3 bucket is NOT fully public (only `/public/*` prefix)
- [ ] Session cookie has `Secure=true`, `HttpOnly=true`, `SameSite=lax`
- [ ] CORS restricted to `https://sites.lenquant.com` only
- [ ] Nginx security headers configured (HSTS, X-Frame-Options, etc.)
- [ ] SSH key-only auth (disable password login)
- [ ] EC2 security group blocks all ports except 22, 80, 443
- [ ] Redis bound to localhost only (not exposed to internet)
- [ ] Regular OS security updates (`unattended-upgrades`)

---

## Scaling Considerations

### When to Scale Up (Vertical)

- CPU consistently >70% → move to `t3.large` (4 vCPU, 8GB)
- Memory consistently >80% → increase instance RAM
- Many concurrent site generations → increase Celery concurrency

### When to Scale Out (Horizontal)

If traffic exceeds single-instance capacity:
1. Move to ALB + multiple EC2 instances
2. Externalize Redis to ElastiCache
3. Run Celery workers on separate instances
4. Consider ECS/Fargate migration at that point

### Performance Tips

- Enable Redis persistence only if needed (currently not needed — broker only)
- Use `gunicorn` with `uvicorn` workers for better process management in production
- Set `CRAWL_TIME_LIMIT_SECONDS` appropriately to avoid hanging jobs
- Monitor Celery queue depth: `docker compose exec redis redis-cli llen celery`
