# CLAUDE.md — ⚙️ back

Backend repo for **SecondBook**. Cross-cutting docs (setup, deployment, architecture overview) → see `../sbook-proto/CLAUDE.md`.

## Commands

Package manager: `uv`. All commands from repo root.

```bash
uv sync                                                      # Install deps
uv sync --group dev                                           # Install dev deps
uv run python textbook_marketplace/manage.py migrate          # Migrations
uv run python textbook_marketplace/manage.py runserver        # Dev server :8000
docker compose up -d                                          # PostgreSQL :10543, Redis :16379

# Tests (must cd into Django root)
cd textbook_marketplace && uv run pytest                      # All tests
cd textbook_marketplace && uv run pytest marketplace/tests.py # Single file
cd textbook_marketplace && uv run pytest -k "test_name"       # Single test
```

Tests use `settings_dev.py` (SQLite, no migrations) via `pytest.ini`. Async tests use `pytest-asyncio`.

## Architecture

```text
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
- **Bidirectional blocking**: block checks both directions before allowing messages
- **Input sanitization**: `bleach` strips HTML from textbook descriptions
- **Image handling**: `django-versatileimagefield` with renditions (preview 240x312, detail 324x420)
- **Rate limiting**: `django-ratelimit` on signup (5/m), token (10/m), refresh (20/m), report (3/m)
- **API docs**: `drf-spectacular` at `/api/docs/` (Swagger UI)

### Settings

- `settings.py` — production (PostgreSQL, restricted CORS, password validators)
- `settings_dev.py` — development (SQLite, `CORS_ALLOW_ALL_ORIGINS=True`, no password validators)
- Environment variables via `python-decouple`: `DJANGO_SECRET_KEY`, `DB_*`, `REDIS_HOST`, `REDIS_PORT`, `FRONTEND_URL`, `MEDIA_HOST`
