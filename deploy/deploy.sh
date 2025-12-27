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
ssh -o StrictHostKeyChecking=no ${SSH_USER}@${SSH_HOST} bash << ENDSSH
  set -e
  DEPLOY_PATH="${DEPLOY_PATH:-/opt/sbook}"
  BACKEND_PATH="\${DEPLOY_PATH}/backend"
  BACKEND_PORT="${BACKEND_PORT:-8000}"
  
  echo "Checking system dependencies..."
  
  # Check required commands and tools
  MISSING_DEPS=""
  
  # Check python3
  if ! command -v python3 &> /dev/null; then
    MISSING_DEPS="\${MISSING_DEPS}python3 "
  fi
  
  # Check curl (needed for health checks)
  if ! command -v curl &> /dev/null; then
    MISSING_DEPS="\${MISSING_DEPS}curl "
  fi
  
  # Check sudo (needed for supervisor commands)
  if ! command -v sudo &> /dev/null; then
    MISSING_DEPS="\${MISSING_DEPS}sudo "
  fi
  
  # Activate uv and check availability
  export UV_HOME="\$HOME/.local/bin"
  if [ -d "\$UV_HOME" ]; then
    export PATH="\$UV_HOME:\$PATH"
  fi
  
  if ! command -v uv &> /dev/null; then
    MISSING_DEPS="\${MISSING_DEPS}uv "
  fi
  
  # Check libmagic1 (required for django-versatileimagefield)
  # Note: This check may not be 100% reliable, but we try to warn early
  # The actual error will be caught during migration if libmagic is missing
  if ! python3 -c "import ctypes.util; lib = ctypes.util.find_library('magic'); exit(0 if lib else 1)" 2>/dev/null; then
    echo "WARNING: libmagic1 may not be installed (required for django-versatileimagefield)"
    echo "  If migrations fail with 'failed to find libmagic', install with:"
    echo "  sudo apt-get update && sudo apt-get install -y libmagic1"
  fi
  
  # Fail fast if dependencies are missing
  if [ -n "\${MISSING_DEPS}" ]; then
    echo "ERROR: Missing required system dependencies: \${MISSING_DEPS}"
    echo ""
    echo "Install missing dependencies:"
    if echo "\${MISSING_DEPS}" | grep -q "uv "; then
      echo "  uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
    fi
    if echo "\${MISSING_DEPS}" | grep -q "python3 "; then
      echo "  python3: sudo apt-get install -y python3"
    fi
    if echo "\${MISSING_DEPS}" | grep -q "curl "; then
      echo "  curl: sudo apt-get install -y curl"
    fi
    if echo "\${MISSING_DEPS}" | grep -q "sudo "; then
      echo "  sudo: sudo apt-get install -y sudo (usually pre-installed)"
    fi
    exit 1
  fi
  
  echo "All system dependencies are available"
  
  cd \${BACKEND_PATH}
  
  echo "Installing dependencies..."
  uv sync
  
  echo "Running migrations..."
  cd textbook_marketplace
  # Create symlink to .env for python-decouple to read it (it looks for .env in current directory)
  if [ -f ../.env ]; then
    ln -sf ../.env .env
  fi
  
  # Create static directory if needed (STATICFILES_DIRS expects this directory)
  echo "Creating static directory if needed..."
  mkdir -p static
  
  uv run python manage.py migrate
  
  echo "Collecting static files..."
  uv run python manage.py collectstatic --noinput
  
  echo "Ensuring superuser exists..."
  uv run python manage.py ensure_superuser
  
  echo "Updating supervisor configuration..."
  # Ensure conf directory exists (we're still in textbook_marketplace, need to go back to backend dir)
  cd ..
  mkdir -p \${DEPLOY_PATH}/conf
  
  # Copy and link supervisor config (we're now in BACKEND_PATH, so deploy/ is relative)
  if [ -f deploy/sbook-backend.supervisor.conf ]; then
    cp deploy/sbook-backend.supervisor.conf \${DEPLOY_PATH}/conf/sbook-backend.supervisor.conf
    sudo ln -sf \${DEPLOY_PATH}/conf/sbook-backend.supervisor.conf /etc/supervisor/conf.d/sbook-backend.conf
    echo "Supervisor configuration updated"
  else
    echo "WARNING: deploy/sbook-backend.supervisor.conf not found"
  fi
  
  echo "Restarting supervisor..."
  sudo supervisorctl reread
  sudo supervisorctl update
  sudo supervisorctl restart sbook-backend || sudo supervisorctl start sbook-backend
  
  echo "Waiting for service to start..."
  sleep 3
  
  echo "Health check..."
  curl -f http://127.0.0.1:\${BACKEND_PORT}/api/health/ || exit 1
  
  echo "Deployment completed successfully"
ENDSSH

echo "Backend deployment finished"
