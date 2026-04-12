# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SecondBook — a textbook marketplace with Django backend and Next.js frontend. Real-time chat via WebSockets, JWT auth, PostgreSQL, Redis.

## Workspace

This is a monorepo-style workspace with two repos:
- **Backend** (this repo): `/home/arezvov/d/projects/sbook/sbook-backend/`
- **Frontend**: `/home/arezvov/d/projects/sbook/sbook-frontend/`

## Backend Commands

Package manager: `uv`. All commands from repo root.

```bash
uv sync                                                      # Install deps
uv sync --group dev                                           # Install dev deps
uv run python textbook_marketplace/manage.py migrate          # Migrations
uv run python textbook_marketplace/manage.py runserver        # Dev server (:8000)
docker-compose up -d                                          # PostgreSQL :10543, Redis :16379

# Tests (must cd into Django root)
cd textbook_marketplace && uv run pytest                      # All tests
cd textbook_marketplace && uv run pytest marketplace/tests.py # Single file
cd textbook_marketplace && uv run pytest -k "test_name"       # Single test

# Test data
uv run python textbook_marketplace/manage.py generate_realistic_data --textbooks 1000
```

Tests use `settings_dev.py` (SQLite, no migrations) via `pytest.ini`. Async tests use `pytest-asyncio`.

## Frontend Commands

Package manager: `pnpm`. Run from the frontend repo root.

```bash
pnpm install            # Install deps
pnpm dev                # Dev server (:3000)
pnpm dev:turbo          # Dev with Turbopack
pnpm build              # Production build
pnpm lint               # ESLint
pnpm test               # Jest unit tests
pnpm test:watch         # Jest watch mode
pnpm test:e2e           # Playwright E2E tests
pnpm test:e2e:ui        # Playwright with UI
```

Environment: `NEXT_PUBLIC_API_BASE_URL` (default `http://127.0.0.1:8000`), `NEXT_PUBLIC_WS_URL` (default `ws://localhost:8000`).

**Important**: `NEXT_PUBLIC_API_BASE_URL` must NOT include `/api` suffix — service paths already include it (e.g. `/api/textbooks/`).

## Backend Architecture

```
textbook_marketplace/           # Django project root (manage.py lives here)
├── textbook_marketplace/       # Project config (settings, urls, asgi)
├── marketplace/                # Core app: users, textbooks, orders, blocks, reports
├── chat/                       # Real-time messaging app
└── api/                        # Thin URL routing layer that includes marketplace + chat
```

### Key Patterns

- **Custom User model** (`marketplace.User`): extends `AbstractUser` with `telegram_id`, `telephone`, `is_seller`
- **JWT auth**: `simplejwt` for REST, `django-channels-jwt-auth-middleware` for WebSocket (token in query param: `ws://host/ws/chat/?token=<jwt>`)
- **WebSocket consumer** (`chat/consumers.py`): `AsyncWebsocketConsumer` with `@database_sync_to_async` for ORM. Channels group layer for broadcasting.
- **Bidirectional blocking**: Block checks both directions before allowing messages
- **Input sanitization**: `bleach` strips HTML from textbook descriptions
- **Image handling**: `django-versatileimagefield` with renditions (preview 240x312, detail 324x420)
- **Rate limiting**: `django-ratelimit` on signup (5/m), token (10/m), refresh (20/m), report (3/m)
- **API docs**: `drf-spectacular` at `/api/docs/` (Swagger UI)

### Settings

- `settings.py` — production (PostgreSQL, restricted CORS, password validators)
- `settings_dev.py` — development (SQLite, `CORS_ALLOW_ALL_ORIGINS=True`, no password validators)
- Environment variables via `python-decouple`: `DJANGO_SECRET_KEY`, `DB_*`, `REDIS_HOST`, `REDIS_PORT`, `FRONTEND_URL`, `MEDIA_HOST`

## Frontend Architecture

Next.js 16 with App Router, React 19, TypeScript.

- **State**: Zustand (`src/stores/userStore.ts`) with localStorage persistence for auth
- **API client**: Axios (`src/services/api.ts`) with auto token refresh on 401
- **WebSocket**: custom singleton (`src/services/websocketService.ts`) with auto-reconnect
- **Validation**: Zod schemas (`src/utils/schemas.ts`)
- **Styling**: Tailwind CSS v4, Font Awesome icons
- **Forms**: Server actions (`src/utils/actions.ts`) with Zod validation

### API Endpoints

REST API at `/api/`:
- `/api/textbooks/` — CRUD with `IsOwner` permission
- `/api/token/`, `/api/token/refresh/` — JWT obtain/refresh
- `/api/signup/` — registration
- `/api/users/me/` — current user
- `/api/users/{username}/block/` — block/unblock
- `/api/wishlist/` — GET list saved textbooks
- `/api/wishlist/{textbook_id}/` — POST add / DELETE remove from wishlist
- `/api/wishlist/{textbook_id}/check/` — GET check if textbook is in wishlist
- `/api/chat/`, `/api/chat/conversation/{username}/` — messages
- WebSocket: `ws/chat/?token=<jwt>`

## Local Development Setup

Step-by-step to get the full stack running locally:

```bash
# 1. Start PostgreSQL and Redis via Docker
docker compose up -d                  # PostgreSQL :10543, Redis :16379

# 2. Install backend dependencies
cd /home/arezvov/d/projects/sbook/sbook-backend
uv sync

# 3. Run migrations (uses production settings with PostgreSQL from Docker)
uv run python textbook_marketplace/manage.py migrate

# 4. Generate test data
uv run python textbook_marketplace/manage.py generate_realistic_data --textbooks 50

# 5. Start backend server
uv run python textbook_marketplace/manage.py runserver 0.0.0.0:8000

# 6. In another terminal — install and start frontend
cd /home/arezvov/d/projects/sbook/sbook-frontend
pnpm install
pnpm dev                              # http://localhost:3000
```

Backend `.env` (repo root): contains `DB_*`, `DJANGO_SECRET_KEY`, `REDIS_*` (already configured for Docker).

Frontend `.env`: `NEXT_PUBLIC_API_BASE_URL="http://127.0.0.1:8000"` — **no `/api` suffix**.

### Notes

- Backend uses `settings.py` (PostgreSQL) by default via `manage.py`. Tests use `settings_dev.py` (SQLite) via `pytest.ini`.
- `settings_dev.py` has broken SQLite config (missing `NAME`), so for local dev use the default `settings.py` with Docker PostgreSQL.
- `MEDIA_HOST` defaults to `http://127.0.0.1:8000` — image URLs in API responses use this prefix. On production must be set to `https://api.sb.maria.rezvov.com`.
- Frontend dev server uses Turbopack by default (`next dev`).

## CI/CD Deployment

Both repos deploy to production via **GitHub Actions** on push to `main` (or manual `workflow_dispatch`).

### Backend Deployment (`.github/workflows/deploy.yml`)

1. Runs tests with PostgreSQL/Redis service containers in CI
2. Collects static files
3. Generates `.env` from GitHub secrets/vars and deploys via SCP
4. Runs `deploy/deploy.sh` which:
   - Rsyncs code to `/opt/sbook/backend/` (excludes `.env`, `media`, `logs`)
   - Runs `uv sync`, `migrate`, `collectstatic`
   - Updates Supervisor config and restarts `sbook-backend`
   - Health check on `/api/health/`

### Frontend Deployment (`.github/workflows/deploy.yml` in frontend repo)

1. Builds with `pnpm build` (bakes `NEXT_PUBLIC_*` env vars)
2. Rsyncs to `/opt/sbook/frontend/` (excludes `.env`, `node_modules`, `.next/cache`)
3. Runs `pnpm install`, restarts PM2 `sbook-frontend`
4. Health check on `http://127.0.0.1:3000`

### Deployment Process

To deploy changes: merge/push to `main` branch → GitHub Actions triggers automatically.

```bash
# Deploy backend
git checkout main && git merge dev && git push origin main

# Deploy frontend (from frontend repo)
cd /home/arezvov/d/projects/sbook/sbook-frontend
git checkout main && git merge dev && git push origin main
```

GitHub Secrets needed: `SSH_PRIVATE_KEY`, `SSH_HOST`, `SSH_USER`, `DJANGO_SECRET_KEY`, `DB_PASSWORD`, `DJANGO_SUPERUSER_PASSWORD`.
GitHub Vars: `DB_NAME`, `DB_USER`, `DB_HOST`, `DB_PORT`, `REDIS_HOST`, `REDIS_PORT`, `FRONTEND_URL`, `MEDIA_HOST`, `BACKEND_DOMAIN`, `DEPLOY_PATH`.

## Production Server

- **SSH**: `ssh sbook@82.146.48.165` (SSH config alias `sbook-dev` has `RemoteCommand` — won't work non-interactively, use direct ssh for commands)
- **Frontend**: `https://sb.maria.rezvov.com` — Next.js via PM2 (`sbook-frontend`) on `:3000`
- **Backend API**: `https://api.sb.maria.rezvov.com` — Daphne ASGI via Supervisor (`sbook-backend`) on `:8000`
- **Nginx**: reverse proxy for both, config at `/opt/sbook/conf/sbook.nginx.conf`
- **Project root**: `/opt/sbook/` (backend: `/opt/sbook/backend/`, frontend: `/opt/sbook/frontend/`)
- **DB/Redis**: native systemd services (PostgreSQL 16, Redis), NOT Docker
- **Logs**: backend at `/opt/sbook/backend/logs/`, frontend via `pm2 logs sbook-frontend`
- **PM2 path**: `/home/sbook/.local/share/pnpm/pm2` (needs `export PATH=$HOME/.local/share/pnpm:$PATH`)
- **SSL**: Let's Encrypt, shared cert for both domains
- **Frontend env**: `/opt/sbook/frontend/.env` (`NEXT_PUBLIC_API_BASE_URL`, `NEXT_PUBLIC_WS_URL`) — `NEXT_PUBLIC_*` vars are baked into the build, must `pnpm build && pm2 restart` after changes
