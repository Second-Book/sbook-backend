#!/bin/bash

: '
This script reads .env file from project root and clears textbook, user and
order tables from postgresql database, then clears media folder from images of
removed textbooks if it exists.

Usage example:

bash rm_db_data.sh
'
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"

env_path="$SCRIPT_DIR/../.env"

if [ -f "$env_path" ]; then
  source "$env_path"
else
  echo "No .env file in project root."
  exit 1
fi

export PGPASSWORD="$DB_PASSWORD"

if [ -z "$PGPASSWORD" ]; then
  echo "Couldn't set PGPASSWORD, check if .env file has DB_PASSWORD var."
  exit 1
else
  echo "PGPASSWORD variable has been successfully set."
fi

if ! command -v psql &> /dev/null; then
  echo "Error: no such command psql. Check if you have psql in PATH of your system."
  exit 1
else
  echo "psql found, proceeding..."
fi

echo "Cleaning marketplace_textbook table"
RM_ROWS_TEXTBOOKS_RES=$(psql -h $DB_HOST -p $DB_PORT -d $DB_NAME -U $DB_USER -c "TRUNCATE TABLE marketplace_textbook CASCADE;")
echo "$RM_ROWS_TEXTBOOKS_RES"

echo "Cleaning marketplace_user table"
RM_ROWS_USERS_RES=$(psql -h $DB_HOST -p $DB_PORT -d $DB_NAME -U $DB_USER -c "TRUNCATE TABLE marketplace_user CASCADE;")
echo "$RM_ROWS_USERS_RES"

echo "Cleaning marketplace_order table"
RM_ROWS_ORDERS_RES=$(psql -h $DB_HOST -p $DB_PORT -d $DB_NAME -U $DB_USER -c "TRUNCATE TABLE marketplace_order CASCADE;")
echo "$RM_ROWS_ORDERS_RES"

echo "Cleaning chat_message table"
RM_ROWS_MESSAGES_RES=$(psql -h $DB_HOST -p $DB_PORT -d $DB_NAME -U $DB_USER -c "TRUNCATE TABLE chat_message CASCADE;")
echo "$RM_ROWS_MESSAGES_RES"

echo "Unsetting PGPASSWORD var..."
unset PGPASSWORD

echo "Cleaning media folder from project..."

media_path="$SCRIPT_DIR/../textbook_marketplace/media"

if [ -d "$media_path" ]; then
  rm -r "$media_path"
  echo "Successfully cleaned."
else
  echo "No media folder found, nothing has been cleaned."
fi