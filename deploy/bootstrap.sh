#!/usr/bin/env bash
# Hermes responder one-shot installer for Ubuntu 24.04.
# Run as root on the target VPS:
#   curl -fsSL https://raw.githubusercontent.com/hatcheric950/T/claude/setup-hermes-agent-emVQB/deploy/bootstrap.sh | bash
# Or after pushing main:
#   curl -fsSL https://raw.githubusercontent.com/hatcheric950/T/main/deploy/bootstrap.sh | bash
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/hatcheric950/T.git}"
BRANCH="${BRANCH:-claude/setup-hermes-agent-emVQB}"
INSTALL_DIR="${INSTALL_DIR:-/opt/hermes}"
ETC_DIR="/etc/hermes"
VAR_DIR="/var/lib/hermes"
LOG_DIR="/var/log/hermes"

if [[ "${EUID}" -ne 0 ]]; then
    echo "must run as root" >&2
    exit 1
fi

echo "[hermes] installing system packages..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y --no-install-recommends \
    python3 python3-venv python3-pip git build-essential libssl-dev curl ca-certificates

echo "[hermes] installing cloudflared..."
if ! command -v cloudflared >/dev/null 2>&1; then
    arch=$(dpkg --print-architecture)
    curl -fsSL "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${arch}.deb" \
        -o /tmp/cloudflared.deb
    dpkg -i /tmp/cloudflared.deb
    rm -f /tmp/cloudflared.deb
fi

echo "[hermes] cloning repo to ${INSTALL_DIR}..."
if [[ -d "${INSTALL_DIR}/.git" ]]; then
    git -C "${INSTALL_DIR}" fetch --depth=1 origin "${BRANCH}"
    git -C "${INSTALL_DIR}" checkout "${BRANCH}"
    git -C "${INSTALL_DIR}" reset --hard "origin/${BRANCH}"
else
    git clone --depth=1 --branch "${BRANCH}" "${REPO_URL}" "${INSTALL_DIR}"
fi

echo "[hermes] creating venv + installing package..."
python3 -m venv "${INSTALL_DIR}/.venv"
"${INSTALL_DIR}/.venv/bin/pip" install --upgrade pip
"${INSTALL_DIR}/.venv/bin/pip" install -e "${INSTALL_DIR}"
ln -sf "${INSTALL_DIR}/.venv/bin/hermes" /usr/local/bin/hermes

echo "[hermes] creating state + secret dirs..."
install -d -m 700 "${ETC_DIR}" "${VAR_DIR}" "${LOG_DIR}"

if [[ ! -f "${ETC_DIR}/allowlist.yaml" ]]; then
    cp "${INSTALL_DIR}/deploy/allowlist.example.yaml" "${ETC_DIR}/allowlist.yaml"
    chmod 600 "${ETC_DIR}/allowlist.yaml"
fi

if [[ ! -f "${ETC_DIR}/env" ]]; then
    cp "${INSTALL_DIR}/deploy/env.example" "${ETC_DIR}/env"
    chmod 600 "${ETC_DIR}/env"
    echo "[hermes] wrote ${ETC_DIR}/env from template — fill in secrets next"
fi

echo "[hermes] installing systemd unit..."
cp "${INSTALL_DIR}/deploy/hermes-watcher.service" /etc/systemd/system/hermes-watcher.service
systemctl daemon-reload
systemctl enable hermes-watcher.service >/dev/null

cat <<EOF

==========================================================================
[hermes] base install complete. Mode is SHADOW by default — no replies
         will be sent until you set HERMES_MODE=live.

NEXT STEPS (do them in order):

  1. Fill in your secrets:
         nano ${ETC_DIR}/env
     Set at minimum:
         ANTHROPIC_API_KEY=...
         GMAIL_ADDRESS=you@gmail.com
         GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx   (Google App Password)
         TWILIO_ACCOUNT_SID=AC...
         TWILIO_AUTH_TOKEN=...
         TWILIO_FROM_NUMBER=+1XXXXXXXXXX
         HERMES_HOSTNAME=hermes.yourdomain.com     (the tunnel hostname)
         TWILIO_WEBHOOK_URL=https://hermes.yourdomain.com/sms/inbound

  2. Add at least one address to the allowlist for shadow testing:
         nano ${ETC_DIR}/allowlist.yaml
     e.g.
         emails:
           - you@gmail.com
         phones:
           - "+15551234567"

  3. Authenticate cloudflared (opens a browser URL — open it on your
     laptop, pick the zone, copy the cert back):
         cloudflared tunnel login

  4. Create the tunnel + route:
         cloudflared tunnel create hermes
         cloudflared tunnel route dns hermes hermes.yourdomain.com
     Then write the tunnel config:
         mkdir -p /etc/cloudflared
         cat >/etc/cloudflared/config.yml <<'CFG'
         tunnel: hermes
         credentials-file: /root/.cloudflared/<TUNNEL-UUID>.json
         ingress:
           - hostname: hermes.yourdomain.com
             service: http://127.0.0.1:8000
           - service: http_status:404
         CFG
         cloudflared service install
         systemctl enable --now cloudflared

  5. Start the watcher:
         systemctl start hermes-watcher
         journalctl -u hermes-watcher -f

  6. Smoke-test:
         curl https://hermes.yourdomain.com/healthz
     (Should return {"status":"ok","mode":"shadow"}.)

  7. Point Twilio's number's "A MESSAGE COMES IN" webhook at:
         https://hermes.yourdomain.com/sms/inbound   (HTTP POST)

  8. Send a test email from an allowlisted address and a test SMS to
     the Twilio number. Watch journalctl — you should see
     "SHADOW would_send" entries with drafted replies, but no actual
     replies will be sent.

  9. After 24h of clean shadow logs, flip to live:
         sed -i 's/^HERMES_MODE=.*/HERMES_MODE=live/' ${ETC_DIR}/env
         systemctl restart hermes-watcher

  Kill switch (blocks all outbound sends instantly):
         touch ${ETC_DIR}/PAUSE
  Resume:
         rm  ${ETC_DIR}/PAUSE
==========================================================================
EOF
