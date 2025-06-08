#!/bin/bash

: '
This script runs django backend tests and allows to see the results for 60
seconds (can be changed).
'
export PYTHONDONTWRITEBYTECODE=1

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"

#echo "Running basic django tests..."
#uv run python "$SCRIPT_DIR/../textbook_marketplace/manage.py" test

echo "Running tests using pytest..."
cd "$SCRIPT_DIR/../textbook_marketplace"
uv run pytest

echo "Done, press Enter to exit..."
read