#!/bin/bash

: '
This script creates fake messages between users. The amount of created units
depends on provided argument. There have to be at least 2 users in database.

Usage example:
bash gen_msgs.sh 5
'

if [ -z "$1" ]; then
  echo "Error, provide amount of messages to generate."
  exit 1
fi

count="$1"
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"

echo "Generating fake messages..."

uv run python "$SCRIPT_DIR/../textbook_marketplace/manage.py" generate_fake_messages $count