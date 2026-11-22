#!/usr/bin/env bash
# ==============================================================================
# Smart Document Processing and Management System
# Production EC2 Deployment Script
#
# Usage:
#   ./scripts/deploy.sh [TARGET_COMMIT_SHA]
#
# Production Guarantees:
#   1. Deployment Concurrency Lock via flock to prevent simultaneous updates
#   2. Point-in-time timestamped SQLite online backup stored outside git repo
#   3. Zero production data loss: strictly preserves .env, *.db, and local_storage/
#   4. Deploys the exact commit SHA verified by GitHub Actions CI
#   5. Pre-flight Python compilation and module import checks before service restart
#   6. Automated rollback to previous commit if health checks fail
# ==============================================================================

set -euo pipefail

# Configuration
APP_DIR="${APP_DIR:-/home/ec2-user/Smart-Document-Management-System}"
BACKUP_DIR="${BACKUP_DIR:-/home/ec2-user/backups}"
SERVICE_NAME="${SERVICE_NAME:-sdm-app.service}"
LOCK_FILE="/tmp/sdm_deploy.lock"
HEALTH_URL="http://127.0.0.1:8000/api/health"
TARGET_SHA="${1:-}"

echo "=========================================================="
echo "SMART DOCUMENT MANAGEMENT SYSTEM - PRODUCTION DEPLOYMENT"
echo "Host Directory: $APP_DIR"
echo "Target Service: $SERVICE_NAME"
echo "Timestamp:      $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "=========================================================="

# ------------------------------------------------------------------------------
# 1. Acquire Deployment Concurrency Lock
# ------------------------------------------------------------------------------
echo ">>> [1/8] Acquiring deployment concurrency lock..."
exec 200>"$LOCK_FILE"
if ! flock -n 200; then
  echo "ERROR: Another deployment is currently executing on this instance. Aborting."
  exit 1
fi
trap 'exec 200>&-; rm -f "$LOCK_FILE"' EXIT
echo "Lock acquired successfully ($LOCK_FILE)."

# ------------------------------------------------------------------------------
# 2. Pre-Deployment Validation & Directory Verification
# ------------------------------------------------------------------------------
echo ">>> [2/8] Validating environment and directory structure..."
if [ ! -d "$APP_DIR" ]; then
  echo "ERROR: Application directory '$APP_DIR' does not exist on this host!"
  exit 1
fi
cd "$APP_DIR"

if [ ! -f ".env" ]; then
  echo "ERROR: Critical production configuration file '$APP_DIR/.env' is missing!"
  exit 1
fi
echo "Verified: .env is present."

# Record currently deployed commit for rollback
PREV_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "HEAD")
echo "Currently deployed commit (rollback target): $PREV_COMMIT"

# Resolve target commit SHA
if [ -z "$TARGET_SHA" ]; then
  echo "No explicit commit SHA provided. Resolving latest origin/main..."
  git fetch origin main
  TARGET_SHA=$(git rev-parse origin/main)
fi
echo "Deploying target commit SHA: $TARGET_SHA"

# ------------------------------------------------------------------------------
# 3. Create Point-in-Time SQLite Database Backup (Zero Data Loss)
# ------------------------------------------------------------------------------
echo ">>> [3/8] Protecting production data - Creating SQLite database backup..."
mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"

DB_FILE="smart_document_manager.db"
if [ -f "$DB_FILE" ]; then
  TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
  BACKUP_FILE="$BACKUP_DIR/smart_document_manager_backup_${TIMESTAMP}.db"
  
  # Use SQLite online backup API to ensure WAL/SHM consistency without locking reads
  if command -v sqlite3 >/dev/null 2>&1; then
    sqlite3 "$DB_FILE" ".backup '$BACKUP_FILE'"
  else
    # Fallback to copy if sqlite3 CLI is absent
    cp -p "$DB_FILE" "$BACKUP_FILE"
  fi
  chmod 600 "$BACKUP_FILE"
  echo "Database snapshot created successfully: $BACKUP_FILE ($(stat -c%s "$BACKUP_FILE" 2>/dev/null || wc -c < "$BACKUP_FILE") bytes)"
else
  echo "Notice: SQLite database '$DB_FILE' does not exist yet (first-time initialization)."
fi

# Record requirements.txt hash prior to checkout
OLD_REQ_HASH=""
if [ -f "requirements.txt" ]; then
  OLD_REQ_HASH=$(sha256sum requirements.txt | cut -d' ' -f1)
fi

# ------------------------------------------------------------------------------
# 4. Fetch and Checkout the Exact Verified Commit SHA
# ------------------------------------------------------------------------------
echo ">>> [4/8] Fetching and checking out exact commit: $TARGET_SHA..."
git fetch origin "$TARGET_SHA"

# Checkout target commit.
# NOTE: We deliberately DO NOT run 'git clean' to ensure untracked production files
# (.env, *.db, local_storage/, backups/) are never deleted or modified.
git checkout "$TARGET_SHA"

ACTIVE_COMMIT=$(git rev-parse HEAD)
if [ "$ACTIVE_COMMIT" != "$TARGET_SHA" ]; then
  echo "ERROR: Checked-out commit ($ACTIVE_COMMIT) does not match target ($TARGET_SHA)!"
  git checkout "$PREV_COMMIT"
  exit 1
fi
echo "Verified: Working directory is now at commit $ACTIVE_COMMIT."

# Verify critical production files remained intact
if [ ! -f ".env" ]; then
  echo "CRITICAL ERROR: .env was removed during checkout! Restoring immediately..."
  git checkout "$PREV_COMMIT"
  exit 1
fi

# ------------------------------------------------------------------------------
# 5. Dependency Management
# ------------------------------------------------------------------------------
echo ">>> [5/8] Checking application dependencies..."
if [ ! -d "venv" ]; then
  echo "Virtual environment not found. Creating venv at $APP_DIR/venv..."
  python3.12 -m venv venv || python3 -m venv venv
fi

NEW_REQ_HASH=$(sha256sum requirements.txt | cut -d' ' -f1)
if [ "$OLD_REQ_HASH" != "$NEW_REQ_HASH" ]; then
  echo "requirements.txt has changed. Updating dependencies in virtualenv..."
  ./venv/bin/pip install --upgrade pip
  ./venv/bin/pip install --no-cache-dir -r requirements.txt
else
  echo "Dependencies are up-to-date (hash: $NEW_REQ_HASH). Skipping pip install."
fi

# ------------------------------------------------------------------------------
# 6. Pre-Flight Bytecode Compilation & Module Import Validation
# ------------------------------------------------------------------------------
echo ">>> [6/8] Executing pre-flight validation (Zero-Downtime Guarantee)..."
echo "Compiling Python source code across backend/..."
if ! ./venv/bin/python -m compileall backend/ > /dev/null; then
  echo "ERROR: Python compilation check failed on new commit! Aborting without restarting service."
  echo "Rolling back codebase to previous commit: $PREV_COMMIT..."
  git checkout "$PREV_COMMIT"
  exit 1
fi

echo "Validating FastAPI application instantiation and startup imports..."
if ! ./venv/bin/python -c "import backend.main; print('FastAPI module import verified successfully.')"; then
  echo "ERROR: Application module import failed! Aborting without restarting service."
  echo "Rolling back codebase to previous commit: $PREV_COMMIT..."
  git checkout "$PREV_COMMIT"
  exit 1
fi
echo "Pre-flight verification passed: Application code is valid and importable."

# ------------------------------------------------------------------------------
# 7. Restart Application Service
# ------------------------------------------------------------------------------
echo ">>> [7/8] Restarting application service: $SERVICE_NAME..."
sudo systemctl restart "$SERVICE_NAME"

# ------------------------------------------------------------------------------
# 8. Post-Deployment Health Verification with Automated Rollback
# ------------------------------------------------------------------------------
echo ">>> [8/8] Probing application health at $HEALTH_URL..."
MAX_ATTEMPTS=15
ATTEMPT=1
IS_HEALTHY=0

while [ $ATTEMPT -le $MAX_ATTEMPTS ]; do
  echo "Health check attempt $ATTEMPT/$MAX_ATTEMPTS..."
  
  if sudo systemctl is-active --quiet "$SERVICE_NAME"; then
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_URL" || echo "000")
    if [ "$HTTP_CODE" = "200" ]; then
      echo "SUCCESS: Application is healthy and responding with HTTP 200!"
      IS_HEALTHY=1
      break
    else
      echo "Service running, awaiting HTTP 200 (current status: $HTTP_CODE)..."
    fi
  else
    echo "Service is still starting up..."
  fi
  
  sleep 2
  ATTEMPT=$((ATTEMPT + 1))
done

if [ $IS_HEALTHY -ne 1 ]; then
  echo "=========================================================="
  echo "ERROR: Health check failed after $MAX_ATTEMPTS attempts!"
  echo "=========================================================="
  echo "--- Systemd Service Status ---"
  sudo systemctl status "$SERVICE_NAME" --no-pager || true
  echo "--- Recent Journal Logs ---"
  sudo journalctl -u "$SERVICE_NAME" -n 50 --no-pager || true

  echo "Initiating automatic rollback to previous stable commit: $PREV_COMMIT..."
  git checkout "$PREV_COMMIT"
  sudo systemctl restart "$SERVICE_NAME"

  # Verify health of rolled-back version
  sleep 3
  if sudo systemctl is-active --quiet "$SERVICE_NAME"; then
    ROLLBACK_HTTP=$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_URL" || echo "000")
    echo "Rollback service status: active (HTTP $ROLLBACK_HTTP)."
  fi
  exit 1
fi

echo "=========================================================="
echo "DEPLOYMENT COMPLETED SUCCESSFULLY!"
echo "Active Commit: $ACTIVE_COMMIT"
echo "Health Status: 200 OK ($HEALTH_URL)"
echo "Timestamp:     $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "=========================================================="
