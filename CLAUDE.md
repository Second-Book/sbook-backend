# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SecondBook — a Django 5.1 textbook marketplace backend with real-time chat via WebSockets. Uses PostgreSQL, Redis, JWT auth, and Django Channels.

## Common Commands

All commands run from the repo root. The project uses `uv` as its package manager.

```bash
# Install dependencies
uv sync

# Run migrations
uv run python textbook_marketplace/manage.py migrate

# Start dev server
uv run python textbook_marketplace/manage.py runserver

# Start infrastructure (PostgreSQL on :10543, Redis on :16379)
docker-compose up

# Run all tests (from repo root)
cd textbook_marketplace && uv run pytest

# Run a single test file
cd textbook_marketplace && uv run pytest marketplace/tests.py

# Run a single test by name
cd textbook_marketplace && uv run pytest -k "test_name"

# Generate test data
uv run python textbook_marketplace/manage.py generate_realistic_data
```

Tests use `settings_dev.py` (SQLite, no migrations) via pytest.ini. Async tests use `pytest-asyncio`.

## Architecture

### Django Project Layout

```
textbook_marketplace/           # Django project root (manage.py lives here)
├── textbook_marketplace/       # Project config (settings, urls, asgi)
├── marketplace/                # Core app: users, textbooks, orders, blocks, reports
├── chat/                       # Real-time messaging app
└── api/                        # Thin URL routing layer that includes marketplace + chat
```

### Key Patterns

- **Custom User model** (`marketplace.User`): extends `AbstractUser` with `telegram_id`, `telephone`, `is_seller`
- **JWT auth**: `simplejwt` for REST, `django-channels-jwt-auth-middleware` for WebSocket (token passed as query param: `ws://host/ws/chat/?token=<jwt>`)
- **WebSocket consumer** (`chat/consumers.py`): `AsyncWebsocketConsumer` with `@database_sync_to_async` for ORM calls. Uses Channels group layer for broadcasting.
- **Bidirectional blocking**: Block checks filter both directions (`initiator→blocked` and `blocked→initiator`) before allowing messages
- **Input sanitization**: `bleach` strips HTML from textbook descriptions
- **Image handling**: `django-versatileimagefield` with defined renditions (preview 240x312, detail 324x420)
- **Rate limiting**: `django-ratelimit` on signup (5/m), token (10/m), refresh (20/m), report (3/m)

### Settings

- `settings.py` — production (PostgreSQL, restricted CORS, password validators enabled)
- `settings_dev.py` — development (SQLite, `CORS_ALLOW_ALL_ORIGINS=True`, no password validators)
- Environment variables via `python-decouple`: `DJANGO_SECRET_KEY`, `DB_*`, `REDIS_HOST`, `REDIS_PORT`, `FRONTEND_URL`

### API Endpoints

REST API is mounted at `/api/`. Key routes:
- `/api/textbooks/` — TextbookViewSet (CRUD with `IsOwner` permission for mutations)
- `/api/token/`, `/api/token/refresh/` — JWT obtain/refresh
- `/api/signup/` — user registration
- `/api/users/me/` — current user profile
- `/api/users/{username}/block/` — block/unblock
- `/api/chat/`, `/api/chat/conversation/{username}/` — message history
- `/api/docs/` — Swagger UI (`drf-spectacular`)
- WebSocket: `ws/chat/?token=<jwt>`
