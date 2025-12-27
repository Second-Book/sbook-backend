#!/bin/bash
set -e

# Change to working directory (supervisor sets this, but be explicit)
cd /opt/sbook/backend/textbook_marketplace

# Note: We don't need to source .env here because Django uses python-decouple
# to read .env file. The .env file should be in the current directory or
# python-decouple will look for it in parent directories.
# We create a symlink to ../.env in deploy.sh, so it should be found.

# Get bind address and port from environment variables with defaults
BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8000}"

# Run daphne
exec uv run daphne -b "${BACKEND_HOST}" -p "${BACKEND_PORT}" textbook_marketplace.asgi:application

