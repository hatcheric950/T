# Deploy: VPS via git pull

The agent itself is **hosted by Anthropic** (Managed Agents API). What you
deploy on the VPS is just a small container that holds your API key and
POSTs the agent definition to `https://api.anthropic.com/v1/agents`.

## One-time bootstrap on the VPS

```bash
ssh you@your-vps
sudo apt-get update && sudo apt-get install -y git docker.io docker-compose-plugin
sudo usermod -aG docker "$USER" && newgrp docker

git clone https://github.com/hatcheric950/T.git ~/field-monitor
cd ~/field-monitor

cp .env.example .env
chmod 600 .env
# edit .env and paste the real sk-ant-... key (from console.anthropic.com)
$EDITOR .env

docker compose build
```

## Create / re-register the agent

```bash
cd ~/field-monitor
docker compose run --rm field-monitor
```

The response (agent id, status) is printed to stdout.

## Updating

From your Mac, commit and push to this branch. On the VPS:

```bash
cd ~/field-monitor
git pull
docker compose build
docker compose run --rm field-monitor
```

## Notes

- `.env` is gitignored — the key never leaves the VPS.
- `create-agent.sh` is a one-shot POST. If you want scheduled agent
  **runs** (the weekly digest), that's a separate endpoint and a cron/
  systemd-timer wrapper — ask and I'll add it.
- To use a different payload, mount or copy a JSON file in and pass its
  path: `docker compose run --rm field-monitor /app/other.json`.
