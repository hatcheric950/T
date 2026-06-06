#!/usr/bin/env bash
set -euo pipefail

: "${ANTHROPIC_API_KEY:?ANTHROPIC_API_KEY must be set (see .env.example)}"

PAYLOAD="${1:-/app/field-monitor.json}"

curl -sS -X POST https://api.anthropic.com/v1/agents \
  -H "Content-Type: application/json" \
  -H "x-api-key: ${ANTHROPIC_API_KEY}" \
  -H "anthropic-version: 2023-06-01" \
  -H "anthropic-beta: managed-agents-2026-04-01" \
  -d "@${PAYLOAD}"
echo
