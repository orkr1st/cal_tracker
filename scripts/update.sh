#!/usr/bin/env bash
# update.sh — Test, build, and redeploy Cal Tracker in one command.
# Usage:  ./scripts/update.sh [--no-cache]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "$ROOT"

BUILD_FLAGS=()
[[ "${1:-}" == "--no-cache" ]] && BUILD_FLAGS+=(--no-cache)

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " Cal Tracker — update pipeline"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── Step 1: Run tests ─────────────────────────────────────────────────────────
echo ""
echo "[ 1/3 ] Running tests (docker build --target test) ..."
docker build "${BUILD_FLAGS[@]}" --target test -t cal_tracker:test .
echo "      ✓ All tests passed"

# ── Step 2: Build production image ───────────────────────────────────────────
echo ""
echo "[ 2/3 ] Building production image ..."
docker build "${BUILD_FLAGS[@]}" --target prod -t cal_tracker:latest .
echo "      ✓ Image built: cal_tracker:latest"

# ── Step 3: Restart the service ───────────────────────────────────────────────
echo ""
echo "[ 3/3 ] Redeploying service ..."
docker compose up -d --force-recreate
echo "      ✓ Service restarted"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " Deployment complete. Running health check ..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Give container a moment to start
sleep 3
if curl -sf http://localhost:5000/api/health > /dev/null; then
    echo " ✓ Health check passed — http://localhost:5000"
else
    echo " ✗ Health check failed. Check: docker compose logs app"
    exit 1
fi
