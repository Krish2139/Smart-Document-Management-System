#!/usr/bin/env bash
# ==============================================================================
# Smart Document Processing and Management System
# EC2 In-Host Deployment Script
#
# Usage:
#   ./scripts/deploy.sh
#
# Guarantees:
#   1. Process lock prevention against simultaneous deployments
#   2. Zero-downtime pre-flight code validation before service restart
#   3. Strict protection of .env, SQLite databases, and local_storage/
#   4. Dynamic dependency installation only when requirements.txt changes
#   5. Automated rollback if health check fails
# ==============================================================================

set -euo pipefail

APP_DIR="${APP_DIR:-/home/ec2-user/Smart-Document-Management-System}"
SERVICE_NAME="${SERVICE_NAME:-sdm-app.service}"
LOCK_FILE="/tmp/sdm_deploy.lock"
HEALTH_URL="http://127.0.0.1:8000/api/health"

echo "=========================================================="
echo ">>> [1/7] ACQUIRING DEPLOYMENT LOCK"
echo "=========================================================="
exec 200>"$LOCK_FILE"
if ! flock -n 200; then
  echo "ERROR: Another deployment process is currently running on this server. Aborting."
  exit 1
fi
trap 'exec 200>&-; rm -f "$LOCK_FILE"' EXIT

echo "=========================================================="
echo ">>> [2/7] PRE-DEPLOYMENT INSPECTION & DIRECTORY CHECK"
echo "=========================================================="
if [ ! -d "$APP_DIR" ]; then
  echo "ERROR: Target directory $APP_DIR does not exist."
  exit 1
fi
cd "$APP_DIR"

if [ ! -f ".env" ]; then
  echo "ERROR: Production environment configuration (.env) is missing in $APP_DIR!"
  exit 1
fi
echo "Verified .env exists. It will remain untouched."

PREV_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "HEAD")
echo "Current deployed commit: $PREV_COMMIT"

OLD_REQ_HASH=""
if [ -f "requirements.txt" ]; then
  OLD_REQ_HASH=$(sha256sum requirements.txt | cut -d' ' -f1)
fi

echo "=========================================================="
echo ">>> [3/7] FETCHING LATEST CODE FROM MAIN"
echo "=========================================================="
git fetch origin main

# Checkout and hard-reset tracked files only.
# Untracked files (.env, *.db, local_storage/) are strictly preserved.
git checkout main
git reset --hard origin/main

NEW_COMMIT=$(git rev-parse HEAD)
echo "Updated codebase to commit: $NEW_COMMIT"

if [ ! -f ".env" ]; then
  echo "ERROR: .env missing after checkout! Rolling back..."
  git reset --hard "$PREV_COMMIT"
  exit 1
fi

echo "=========================================================="
echo ">>> [4/7] DEPENDENCY MANAGEMENT"
echo "=========================================================="
if [ ! -d "venv" ]; then
  echo "Virtual environment not found. Initializing at $APP_DIR/venv..."
  python3.12 -m venv venv || python3 -m venv venv
fi

NEW_REQ_HASH=$(sha256sum requirements.txt | cut -d' ' -f1)
if [ "$OLD_REQ_HASH" != "$NEW_REQ_HASH" ]; then
  echo "requirements.txt updated ($OLD_REQ_HASH -> $NEW_REQ_HASH). Updating dependencies..."
  ./venv/bin/pip install --upgrade pip
  ./venv/bin/pip install --no-cache-dir -r requirements.txt
else
  echo "Dependencies unchanged. Skipping pip install."
fi

echo "=========================================================="
echo ">>> [5/7] PRE-FLIGHT VALIDATION"
echo "=========================================================="
echo "Compiling Python source code..."
if ! ./venv/bin/python -m compileall backend/ > /dev/null; then
  echo "ERROR: Python compilation check failed! Rolling back to $PREV_COMMIT..."
  git reset --hard "$PREV_COMMIT"
  exit 1
fi

echo "Testing FastAPI module import..."
if ! ./venv/bin/python -c "import backend.main; print('FastAPI module import verified successfully.')"; then
  echo "ERROR: Application import verification failed! Rolling back to $PREV_COMMIT..."
  git reset --hard "$PREV_COMMIT"
  exit 1
fi

echo "=========================================================="
echo ">>> [6/7] RESTARTING SYSTEMD SERVICE ($SERVICE_NAME)"
echo "=========================================================="
sudo systemctl restart "$SERVICE_NAME"

echo "=========================================================="
echo ">>> [7/7] POST-DEPLOYMENT HEALTH VERIFICATION"
echo "=========================================================="
MAX_ATTEMPTS=15
ATTEMPT=1
IS_HEALTHY=0

while [ $ATTEMPT -le $MAX_ATTEMPTS ]; do
  echo "Health check probe $ATTEMPT/$MAX_ATTEMPTS..."
  if sudo systemctl is-active --quiet "$SERVICE_NAME"; then
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_URL" || echo "000")
    if [ "$HTTP_CODE" = "200" ]; then
      echo "Health check PASSED with HTTP 200 from $HEALTH_URL!"
      IS_HEALTHY=1
      break
    else
      echo "Service running, awaiting HTTP 200 (current: $HTTP_CODE)..."
    fi
  else
    echo "Service initializing..."
  fi
  sleep 2
  ATTEMPT=$((ATTEMPT + 1))
done

if [ $IS_HEALTHY -ne 1 ]; then
  echo "ERROR: Post-deployment health check failed after $MAX_ATTEMPTS attempts!"
  echo "--- Systemd Service Status ---"
  sudo systemctl status "$SERVICE_NAME" --no-pager || true
  echo "--- Recent Journal Logs ---"
  sudo journalctl -u "$SERVICE_NAME" -n 50 --no-pager || true

  echo "Executing automatic rollback to $PREV_COMMIT..."
  git reset --hard "$PREV_COMMIT"
  sudo systemctl restart "$SERVICE_NAME"
  exit 1
fi

echo "=========================================================="
echo "DEPLOYMENT COMPLETED SUCCESSFULLY!"
echo "Active commit: $NEW_COMMIT"
echo "=========================================================="
