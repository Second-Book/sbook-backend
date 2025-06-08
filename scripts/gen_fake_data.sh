#!/bin/bash

: '
This script creates fake users, fake textbooks and fake messages. The amount of created units
depends on provided argument.

Usage example:
bash gen_fake_data.sh 5
'

if [ -z "$1" ]; then
  echo "Error, provide amount of users, textbooks and messages to generate."
  exit 1
fi

count="$1"
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"

echo "Generating fake users..."
uv run python "$SCRIPT_DIR/../textbook_marketplace/manage.py" generate_fake_users $count

echo "Generating fake textbooks..."
uv run python "$SCRIPT_DIR/../textbook_marketplace/manage.py" generate_fake_textbooks $count

echo "Generating fake messages..."
uv run python "$SCRIPT_DIR/../textbook_marketplace/manage.py" generate_fake_messages $count