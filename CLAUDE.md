# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SecondBook — a textbook marketplace with Django backend and Next.js frontend. Real-time chat via WebSockets, JWT auth, PostgreSQL, Redis.

## Workspace

This is a monorepo-style workspace with two repos:
- **Backend** (this repo): `/home/arezvov/d/projects/sbook/textbook-marketplace-backend/`
- **Frontend**: `/home/arezvov/d/projects/sbook/textbook-marketplace-frontend/`

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

Environment: `NEXT_PUBLIC_API_BASE_URL` (default `http://127.0.0.1:8000/api`), `NEXT_PUBLIC_WS_URL` (default `ws://localhost:8000`).

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
- Environment variables via `python-decouple`: `DJANGO_SECRET_KEY`, `DB_*`, `REDIS_HOST`, `REDIS_PORT`, `FRONTEND_URL`

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
- `/api/chat/`, `/api/chat/conversation/{username}/` — messages
- WebSocket: `ws/chat/?token=<jwt>`

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
