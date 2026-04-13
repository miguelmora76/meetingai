#!/usr/bin/env bash
# Deploy EngineerAI to Kubernetes (Docker Desktop).
#
# Usage:
#   export ANTHROPIC_API_KEY=sk-ant-...
#   export ADMIN_TOKEN=your-strong-token
#   ./scripts/k8s-apply.sh
#
# All other variables are optional — see k8s/secret.yaml for the full list.
# Values default: POSTGRES_USER/PASSWORD → "meetingai", Slack vars → ""
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
K8S_DIR="$SCRIPT_DIR/../k8s"

# ── Validate required env vars ────────────────────────────────────────────────
error=0
for var in ANTHROPIC_API_KEY ADMIN_TOKEN; do
  if [[ -z "${!var:-}" ]]; then
    echo "ERROR: \$$var is not set" >&2
    error=1
  fi
done
[[ $error -eq 1 ]] && echo "Set the missing variables and re-run." >&2 && exit 1

# ── Apply manifests ───────────────────────────────────────────────────────────
echo "Applying namespace..."
kubectl apply -f "$K8S_DIR/namespace.yaml"

echo "Applying configmap..."
kubectl apply -f "$K8S_DIR/configmap.yaml"

echo "Applying secrets (rendered from environment)..."
envsubst < "$K8S_DIR/secret.yaml" | kubectl apply -f -

echo "Applying postgres..."
kubectl apply -f "$K8S_DIR/postgres.yaml"

echo "Applying app..."
kubectl apply -f "$K8S_DIR/app.yaml"

echo ""
echo "Waiting for rollout..."
kubectl rollout status deployment/meetingai-app -n meetingai

echo ""
echo "Done. App available at http://localhost:8000"
