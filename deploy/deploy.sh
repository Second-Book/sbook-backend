#!/bin/bash
set -e

# Configuration
SSH_HOST="${SSH_HOST}"
SSH_USER="${SSH_USER}"
DEPLOY_PATH="${DEPLOY_PATH:-/opt/sbook}"
BACKEND_PATH="${DEPLOY_PATH}/backend"

echo "Deploying backend to ${SSH_USER}@${SSH_HOST}:${BACKEND_PATH}"

# Create directory structure on server
ssh -o StrictHostKeyChecking=no ${SSH_USER}@${SSH_HOST} << ENDSSH
  set -e
  DEPLOY_PATH="${DEPLOY_PATH:-/opt/sbook}"
  BACKEND_PATH="\${DEPLOY_PATH}/backend"
  
  mkdir -p \${BACKEND_PATH}/logs
  mkdir -p \${DEPLOY_PATH}/conf
ENDSSH

# Copy application files
echo "Copying application files..."
rsync -avz --delete \
  --exclude='.git' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.env' \
  --exclude='media' \
  --exclude='logs' \
  --exclude='node_modules' \
  --exclude='.next' \
  ./ ${SSH_USER}@${SSH_HOST}:${BACKEND_PATH}/

# Deploy on server
# Pass environment variables to remote server via env command
env DJANGO_SECRET_KEY="${DJANGO_SECRET_KEY}" \
    DEBUG="${DEBUG:-False}" \
    DB_NAME="${DB_NAME:-sbook}" \
    DB_USER="${DB_USER:-sbook}" \
    DB_PASSWORD="${DB_PASSWORD}" \
    DB_HOST="${DB_HOST:-localhost}" \
    DB_PORT="${DB_PORT:-5432}" \
    REDIS_HOST="${REDIS_HOST:-localhost}" \
    REDIS_PORT="${REDIS_PORT:-6379}" \
    FRONTEND_URL="${FRONTEND_URL:-https://sb.maria.rezvov.com}" \
    DEPLOY_PATH="${DEPLOY_PATH:-/opt/sbook}" \
    BACKEND_PORT="${BACKEND_PORT:-8000}" \
  ssh -o StrictHostKeyChecking=no ${SSH_USER}@${SSH_HOST} bash << 'ENDSSH'
  set -e
  DEPLOY_PATH="${DEPLOY_PATH:-/opt/sbook}"
  BACKEND_PATH="${DEPLOY_PATH}/backend"
  
  export DJANGO_SECRET_KEY
  export DEBUG
  export DB_NAME
  export DB_USER
  export DB_PASSWORD
  export DB_HOST
  export DB_PORT
  export REDIS_HOST
  export REDIS_PORT
  export FRONTEND_URL
  
  cd ${BACKEND_PATH}
  
  # Activate uv if not in PATH
  if ! command -v uv &> /dev/null; then
    export PATH="$HOME/.local/bin:$PATH"
    if [ -f "$HOME/.local/bin/env" ]; then
      source "$HOME/.local/bin/env"
    fi
  fi
  
  echo "Installing dependencies..."
  uv sync
  
  echo "Running migrations..."
  cd textbook_marketplace
  env DJANGO_SECRET_KEY="${DJANGO_SECRET_KEY}" \
      DEBUG="${DEBUG}" \
      DB_NAME="${DB_NAME}" \
      DB_USER="${DB_USER}" \
      DB_PASSWORD="${DB_PASSWORD}" \
      DB_HOST="${DB_HOST}" \
      DB_PORT="${DB_PORT}" \
      REDIS_HOST="${REDIS_HOST}" \
      REDIS_PORT="${REDIS_PORT}" \
      FRONTEND_URL="${FRONTEND_URL}" \
    uv run python manage.py migrate
  
  echo "Collecting static files..."
  env DJANGO_SECRET_KEY="${DJANGO_SECRET_KEY}" \
      DEBUG="${DEBUG}" \
      DB_NAME="${DB_NAME}" \
      DB_USER="${DB_USER}" \
      DB_PASSWORD="${DB_PASSWORD}" \
      DB_HOST="${DB_HOST}" \
      DB_PORT="${DB_PORT}" \
      REDIS_HOST="${REDIS_HOST}" \
      REDIS_PORT="${REDIS_PORT}" \
      FRONTEND_URL="${FRONTEND_URL}" \
    uv run python manage.py collectstatic --noinput
  
  echo "Updating supervisor configuration..."
  if [ -f deploy/sbook-backend.supervisor.conf ]; then
    cp deploy/sbook-backend.supervisor.conf ${DEPLOY_PATH}/conf/sbook-backend.supervisor.conf
    # Add environment variables to supervisor config
    cat >> ${DEPLOY_PATH}/conf/sbook-backend.supervisor.conf << SUPERVISOR_ENV
environment=DJANGO_SECRET_KEY="${DJANGO_SECRET_KEY}",DEBUG="${DEBUG}",DB_NAME="${DB_NAME}",DB_USER="${DB_USER}",DB_PASSWORD="${DB_PASSWORD}",DB_HOST="${DB_HOST}",DB_PORT="${DB_PORT}",REDIS_HOST="${REDIS_HOST}",REDIS_PORT="${REDIS_PORT}",FRONTEND_URL="${FRONTEND_URL}"
SUPERVISOR_ENV
    sudo ln -sf ${DEPLOY_PATH}/conf/sbook-backend.supervisor.conf /etc/supervisor/conf.d/sbook-backend.conf
  fi
  
  echo "Restarting supervisor..."
  sudo supervisorctl reread
  sudo supervisorctl update
  sudo supervisorctl restart sbook-backend || sudo supervisorctl start sbook-backend
  
  echo "Waiting for service to start..."
  sleep 3
  
  echo "Health check..."
  curl -f http://127.0.0.1:${BACKEND_PORT}/api/health/ || exit 1
  
  echo "Deployment completed successfully"
ENDSSH

echo "Backend deployment finished"
