#!/usr/bin/env bash
# Hermes SessionStart hook: ensure the project is installed and runnable.
# Must never fail the session — always exits 0.
set +e

echo "[hermes:session-start] installing project (editable + dev extras)..."
python -m pip install -q -e ".[dev]" 2>/tmp/hermes-pip.log
status=$?

if [ $status -ne 0 ]; then
  echo "[hermes:session-start] WARNING: pip install failed (offline?); continuing."
  tail -n 3 /tmp/hermes-pip.log 2>/dev/null
  exit 0
fi

ver="$(hermes --version 2>/dev/null || echo 'hermes (version unavailable)')"
echo "[hermes:session-start] ready: ${ver}"
exit 0
