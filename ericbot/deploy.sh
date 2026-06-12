#!/usr/bin/env bash
# EricBot VPS deployment bootstrap
# Run as root on HERMES (Debian 12): bash deploy.sh YOUR_DOMAIN
# e.g. bash deploy.sh bot.ericdomain.com
set -e

DOMAIN=${1:-"YOUR_DOMAIN"}
REPO="https://github.com/hatcheric950/T.git"
INSTALL_DIR="/opt/ericbot"

echo "==> EricBot deploying to $DOMAIN"

# ── 1. Docker ------------------------------------------------------------------
if ! command -v docker &>/dev/null; then
    echo "==> Installing Docker..."
    curl -fsSL https://get.docker.com | sh
fi
if ! docker compose version &>/dev/null; then
    echo "==> Installing docker-compose-plugin..."
    apt-get install -y docker-compose-plugin
fi

# ── 2. Clone / update repo -----------------------------------------------------
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "==> Pulling latest code..."
    git -C "$INSTALL_DIR" pull
else
    echo "==> Cloning repo..."
    git clone "$REPO" "$INSTALL_DIR"
fi

cd "$INSTALL_DIR/ericbot"

# ── 3. .env -------------------------------------------------------------------
if [ ! -f .env ]; then
    echo ""
    echo "  !! .env not found."
    echo "  Copy your .env file to $INSTALL_DIR/ericbot/.env then re-run this script."
    echo "  Example from your local machine:"
    echo "    scp ericbot/.env root@15.204.245.5:$INSTALL_DIR/ericbot/.env"
    echo ""
    exit 1
fi

# ── 4. Build + start -----------------------------------------------------------
echo "==> Building and starting EricBot..."
docker compose up -d --build

echo "==> Waiting for health check..."
sleep 5
curl -sf http://localhost:8000/api/health && echo " ✓ EricBot is up" || echo " ✗ Health check failed — run: docker compose logs ericbot"

# ── 5. nginx ------------------------------------------------------------------
echo "==> Configuring nginx..."
apt-get install -y nginx certbot python3-certbot-nginx

mkdir -p /var/www/certbot

# Write nginx config with real domain substituted
sed "s/YOUR_DOMAIN/$DOMAIN/g" nginx/ericbot.conf > /etc/nginx/sites-available/ericbot
ln -sf /etc/nginx/sites-available/ericbot /etc/nginx/sites-enabled/ericbot
rm -f /etc/nginx/sites-enabled/default   # remove default placeholder if present

nginx -t
systemctl enable nginx
systemctl reload nginx

# ── 6. SSL (Let's Encrypt) ----------------------------------------------------
echo "==> Obtaining SSL certificate for $DOMAIN..."
certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m "$(grep ERIC_PHONE_NUMBER .env | cut -d= -f2 | tr -d '+' || echo admin)@example.com" || {
    echo "  Certbot failed — make sure your DNS A record for $DOMAIN points to 15.204.245.5"
    echo "  Once DNS propagates, run manually: certbot --nginx -d $DOMAIN"
}

echo ""
echo "==> Done! EricBot is live at https://$DOMAIN"
echo ""
echo "  Set these webhook URLs:"
echo "    Twilio SMS:     https://$DOMAIN/api/sms/webhook"
echo "    Zoom Phone:     https://$DOMAIN/api/calls/webhook"
echo ""
echo "  Useful commands:"
echo "    docker compose logs -f ericbot     # tail logs"
echo "    docker compose restart ericbot     # restart"
echo "    docker compose pull && docker compose up -d --build  # update"
