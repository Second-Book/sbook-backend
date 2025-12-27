#!/bin/bash
set -e

# Load environment from .env file
set -a
source /opt/sbook/backend/.env
set +a

# Change to working directory (supervisor sets this, but be explicit)
cd /opt/sbook/backend/textbook_marketplace

# Run daphne
exec uv run daphne -b 127.0.0.1 -p 8000 textbook_marketplace.asgi:application

