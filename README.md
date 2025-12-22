# Textbook Marketplace Backend

Django REST API backend for textbook marketplace application.

## Prerequisites

MUST install:

- Python 3.12
- uv package manager
- Docker and docker-compose
- PostgreSQL client (psql) for database scripts

## Environment Setup

Copy `env.example` to `.env`:

```bash
cp env.example .env
```

Update `.env` with actual values. MUST set `DJANGO_SECRET_KEY`:

```bash
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

Required variables:

- `DJANGO_SECRET_KEY` (MUST be set)
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` (PostgreSQL)
- `REDIS_HOST`, `REDIS_PORT` (Redis)

Optional variables (defaults in settings):

- `FRONTEND_URL` (default: http://localhost:3000)
- `DEBUG` (default: False)
- `STATIC_ROOT`, `MEDIA_ROOT`, `MEDIA_HOST`

Default database credentials (from docker-compose.yml): `textbook/textbook` on port `10543`. Redis on port `16379`.

## Installation

Install dependencies:

```bash
uv sync
```

Install dev dependencies:

```bash
uv sync --group dev
```

## Database Setup

Start services:

```bash
docker-compose up -d
```

Run migrations:

```bash
uv run python textbook_marketplace/manage.py migrate
```

Verify containers running:

- `textbook_postgres` on port `10543`
- `textbook_redis` on port `16379`

## Superuser Creation

Use script (Windows Git Bash):

```bash
bash scripts/gen_suser.sh
```

Manual creation:

```bash
uv run python textbook_marketplace/manage.py createsuperuser
```

Default credentials: `username=root`, `email=root@example.com`.

## Test Data Generation

Generate N users, textbooks, and messages:

```bash
bash scripts/gen_fake_data.sh N
```

Clean database and regenerate:

```bash
bash scripts/clean_and_gen.sh N
```

Individual commands:

```bash
uv run python textbook_marketplace/manage.py generate_fake_users N
uv run python textbook_marketplace/manage.py generate_fake_textbooks N
uv run python textbook_marketplace/manage.py generate_fake_messages N
```

## Running Server

Development:

```bash
bash scripts/run.sh
```

Or directly:

```bash
uv run python textbook_marketplace/manage.py runserver
```

Server runs on `http://127.0.0.1:8000`.

Settings: `textbook_marketplace.settings_dev` (dev) or `textbook_marketplace.settings` (production).

## API Testing with curl

Base URL: `http://127.0.0.1:8000/api/`

Swagger documentation: `http://127.0.0.1:8000/api/docs/`

### Signup

```bash
curl -X POST http://127.0.0.1:8000/api/signup/ \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "email": "test@example.com", "password": "testpass123"}'
```

### Login

```bash
curl -X POST http://127.0.0.1:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "testpass123"}'
```

Response includes `access` and `refresh` tokens.

### Get Textbooks

```bash
curl http://127.0.0.1:8000/api/textbooks/
```

### Protected Endpoint (requires JWT)

```bash
curl http://127.0.0.1:8000/api/protected/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Refresh Token

```bash
curl -X POST http://127.0.0.1:8000/api/token/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh": "YOUR_REFRESH_TOKEN"}'
```

### Get Current User

```bash
curl http://127.0.0.1:8000/api/users/me/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Testing

Run tests:

```bash
bash scripts/run_tests.sh
```

Or directly:

```bash
cd textbook_marketplace
uv run pytest
```

Test location: `textbook_marketplace/` directory. Config: `pytest.ini`.

## Scripts

All scripts in `scripts/` directory:

- `run.sh` - Start development server
- `gen_suser.sh` - Create superuser (Windows Git Bash)
- `gen_fake_data.sh N` - Generate N users, textbooks, messages
- `clean_and_gen.sh N` - Clean database and generate N test records
- `rm_db_data.sh` - Remove all data from database (requires .env with DB credentials)
- `run_tests.sh` - Run pytest tests

## Additional Information

Project structure: Django app with `marketplace` and `chat` apps.

WebSocket support: Django Channels with Redis channel layer.

Media files: stored in `textbook_marketplace/media/`.

Static files: collected to `staticfiles/`.

Database cleanup: `bash scripts/rm_db_data.sh` (requires .env with DB credentials).

## Files Reference

- [docker-compose.yml](docker-compose.yml) - Database and Redis configuration
- [pyproject.toml](pyproject.toml) - Dependencies and Python version
- [scripts/](scripts/) - Helper scripts for common tasks
- [textbook_marketplace/textbook_marketplace/settings.py](textbook_marketplace/textbook_marketplace/settings.py) - Production settings
- [textbook_marketplace/textbook_marketplace/settings_dev.py](textbook_marketplace/textbook_marketplace/settings_dev.py) - Development settings
- [env.example](env.example) - Environment variables template

