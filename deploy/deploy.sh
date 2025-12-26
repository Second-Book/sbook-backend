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
ssh -o StrictHostKeyChecking=no ${SSH_USER}@${SSH_HOST} << ENDSSH
  set -e
  DEPLOY_PATH="${DEPLOY_PATH:-/opt/sbook}"
  BACKEND_PATH="\${DEPLOY_PATH}/backend"
  
  cd \${BACKEND_PATH}
  
  echo "Installing dependencies..."
  uv sync
  
  echo "Running migrations..."
  cd textbook_marketplace
  uv run python manage.py migrate
  
  echo "Collecting static files..."
  uv run python manage.py collectstatic --noinput
  
  echo "Updating supervisor configuration..."
  if [ -f deploy/sbook-backend.supervisor.conf ]; then
    cp deploy/sbook-backend.supervisor.conf \${DEPLOY_PATH}/conf/sbook-backend.supervisor.conf
    sudo ln -sf \${DEPLOY_PATH}/conf/sbook-backend.supervisor.conf /etc/supervisor/conf.d/sbook-backend.conf
  fi
  
  echo "Restarting supervisor..."
  sudo supervisorctl reread
  sudo supervisorctl update
  sudo supervisorctl restart sbook-backend || sudo supervisorctl start sbook-backend
  
  echo "Waiting for service to start..."
  sleep 3
  
  echo "Health check..."
  BACKEND_PORT="${BACKEND_PORT:-8000}"
  curl -f http://127.0.0.1:\${BACKEND_PORT}/api/health/ || exit 1
  
  echo "Deployment completed successfully"
ENDSSH

echo "Backend deployment finished"

