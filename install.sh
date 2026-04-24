#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────
# Rhodawk EmbodiedOS — one-shot VPS installer.
# Usage (from a fresh Ubuntu 22.04 / Debian 12 VPS, as a sudo user):
#
#   curl -fsSL https://raw.githubusercontent.com/Rhodawk-AI/Rhodawk-devops-engine/main/install.sh | bash
#
# Or after `git clone`, just run `bash install.sh`.
# ──────────────────────────────────────────────────────────────────────────
set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-/opt/rhodawk}"
REPO_URL="${REPO_URL:-https://github.com/Rhodawk-AI/Rhodawk-devops-engine.git}"
HOST_PORT="${HOST_PORT:-7860}"

log()  { printf '\033[1;36m[rhodawk]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[rhodawk]\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[rhodawk]\033[0m %s\n' "$*" >&2; exit 1; }

[[ $EUID -ne 0 ]] || die "Run as a non-root user with sudo, not as root."
command -v sudo >/dev/null || die "sudo is required."

log "1/6  Installing Docker + Compose + git…"
sudo apt update -y
sudo apt install -y ca-certificates curl gnupg git ufw

if ! command -v docker >/dev/null; then
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
        sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
        sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt update -y
    sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    sudo usermod -aG docker "$USER"
    warn "Added $USER to the docker group. You may need to log out and back in."
fi

log "2/6  Cloning repo into ${INSTALL_DIR}…"
if [[ ! -d "${INSTALL_DIR}/.git" ]]; then
    sudo mkdir -p "$(dirname "${INSTALL_DIR}")"
    sudo git clone "${REPO_URL}" "${INSTALL_DIR}"
    sudo chown -R "$USER":"$USER" "${INSTALL_DIR}"
else
    log "    already cloned — pulling latest"
    git -C "${INSTALL_DIR}" pull --ff-only
fi
cd "${INSTALL_DIR}"

log "3/6  Preparing .env…"
if [[ ! -f .env ]]; then
    cp .env.example .env
    warn "Edit ${INSTALL_DIR}/.env now and set DO_INFERENCE_API_KEY and GITHUB_TOKEN."
    warn "Press <Enter> when done…"
    read -r _
fi

# Sanity-check required keys before we burn 10 minutes on a build.
set -a; . ./.env; set +a
[[ -n "${DO_INFERENCE_API_KEY:-}${OPENROUTER_API_KEY:-}" ]] \
    || die "Neither DO_INFERENCE_API_KEY nor OPENROUTER_API_KEY is set in .env."
[[ -n "${GITHUB_TOKEN:-}" ]] \
    || die "GITHUB_TOKEN is not set in .env."

log "4/6  Opening firewall on port ${HOST_PORT}…"
sudo ufw allow OpenSSH || true
sudo ufw allow "${HOST_PORT}/tcp" || true
sudo ufw --force enable

log "5/6  Writing docker-compose.yml (if missing)…"
if [[ ! -f docker-compose.yml ]]; then
    cat > docker-compose.yml <<YAML
services:
  rhodawk:
    build: .
    image: rhodawk:latest
    container_name: rhodawk
    restart: unless-stopped
    env_file: .env
    ports:
      - "\${HOST_PORT:-7860}:7860"
    volumes:
      - rhodawk-data:/data
      - rhodawk-logs:/tmp
    healthcheck:
      test: ["CMD", "curl", "-fsS", "http://localhost:7860/"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 60s

volumes:
  rhodawk-data:
  rhodawk-logs:
YAML
fi

log "6/6  Building and starting the container…"
docker compose build
docker compose up -d

log "Done. Tailing logs (Ctrl+C to stop tailing — the container keeps running)…"
docker compose logs -f rhodawk
