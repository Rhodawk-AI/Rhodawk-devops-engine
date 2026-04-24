# Deploying Rhodawk EmbodiedOS on a VPS

> *Anyone with a fresh Linux box, a `DO_INFERENCE_API_KEY`, and a `GITHUB_TOKEN` can have the full Rhodawk DevSecOps engine running in under 15 minutes.*

This guide is **end-to-end**. It covers a brand-new Ubuntu 22.04 / Debian 12 VPS from `apt update` through to a running Gradio UI on `https://your-vps.example.com`. Every command is copy-pasteable.

---

## 0. What you need before you start

- A VPS with **at least**: 4 vCPU, 8 GB RAM, 40 GB SSD (16 GB RAM strongly recommended for Hermes + meta-learner concurrent).
- Root or `sudo` access.
- Two API keys:
    1. **`DO_INFERENCE_API_KEY`** — DigitalOcean Serverless Inference. Get one at <https://cloud.digitalocean.com/gen-ai/agents> → **Inference** → **API Keys**.
    2. **`GITHUB_TOKEN`** — A GitHub personal access token with scopes **`repo`** and **`security_events`**.
- *(Optional but recommended)* an **`OPENROUTER_API_KEY`** to unlock the OR-only members of the Model Squad (`kimi-k2.5`, `claude-4.6-sonnet`, `minimax-m2.5`).

---

## 1. Install Docker + Compose

```bash
sudo apt update
sudo apt install -y ca-certificates curl gnupg git ufw

# Docker official repo
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
    sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
    sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Let your shell user run docker without sudo
sudo usermod -aG docker "$USER"
newgrp docker

docker --version          # sanity check
docker compose version
```

---

## 2. Clone the repo

```bash
cd /opt
sudo git clone https://github.com/Rhodawk-AI/Rhodawk-devops-engine.git rhodawk
sudo chown -R "$USER":"$USER" rhodawk
cd rhodawk
```

---

## 3. Configure your secrets

```bash
cp .env.example .env
nano .env
```

At minimum set:

```ini
DO_INFERENCE_API_KEY=do_infer_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# Optional but unlocks the OR-only models in the squad:
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Save and exit (`Ctrl+O`, `Enter`, `Ctrl+X`).

---

## 4. Open the firewall

The Gradio UI binds to port 7860 inside the container. We expose it on host port 7860.

```bash
sudo ufw allow OpenSSH
sudo ufw allow 7860/tcp
sudo ufw --force enable
sudo ufw status
```

---

## 5. Build and run with Docker Compose

A minimal `docker-compose.yml` is bundled in the repo. If it isn't there yet, create it:

```bash
cat > docker-compose.yml <<'YAML'
services:
  rhodawk:
    build: .
    image: rhodawk:latest
    container_name: rhodawk
    restart: unless-stopped
    env_file: .env
    ports:
      - "${HOST_PORT:-7860}:7860"
    volumes:
      - rhodawk-data:/data
      - rhodawk-logs:/tmp
    # OpenClaude / Camofox / G0DM0D3 daemons run inside the container; no extra ports needed.
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
```

Build and start:

```bash
docker compose build       # ~5–10 minutes the first time
docker compose up -d
docker compose logs -f rhodawk
```

When you see `Running on local URL:  http://0.0.0.0:7860`, the engine is alive.

Visit:

```
http://YOUR_VPS_IP:7860
```

Click into **🧬 EmbodiedOS** and start typing missions.

---

## 6. Verify the Model Squad is wired correctly

From the host:

```bash
docker compose exec rhodawk env | grep -E '^(DO_INFERENCE|OPENROUTER|EXECUTION|HERMES|RECON|TRIAGE|FALLBACK)_' | sort
docker compose exec rhodawk python - <<'PY'
from llm_router import chat_text
print(chat_text("EXECUTION", "Reply with the single word: ready."))
PY
```

A successful reply means DO is reachable and your key is good. If you see `[llm_router] no provider available …`, recheck `.env`.

---

## 7. Put it behind HTTPS (Caddy — easiest path)

Recommended only after step 6 succeeds. This gives you `https://rhodawk.example.com` with auto-renewing TLS.

```bash
sudo apt install -y caddy
sudo tee /etc/caddy/Caddyfile <<'CADDY'
rhodawk.example.com {
    reverse_proxy 127.0.0.1:7860
    encode gzip
}
CADDY

sudo systemctl reload caddy
```

Point an A record for `rhodawk.example.com` at your VPS IP. Caddy will mint a Let's Encrypt cert automatically on the first request. You can now close port 7860 in `ufw` (`sudo ufw delete allow 7860/tcp`) and only expose 80/443.

---

## 8. Day-2 operations

```bash
# tail logs (Gradio + every daemon)
docker compose logs -f rhodawk

# restart cleanly (preserves /data)
docker compose restart rhodawk

# pull latest code, rebuild, redeploy
cd /opt/rhodawk
git pull
docker compose build
docker compose up -d

# back up persistent data (Hermes sessions, audit chain, harvester state, vault)
docker run --rm -v rhodawk-data:/data -v "$PWD":/backup alpine \
    tar czf /backup/rhodawk-data-$(date +%F).tgz -C /data .

# stop the engine
docker compose down

# nuke everything (⚠ deletes vault, audit chain, harvester history)
docker compose down -v
```

### Health endpoints baked into the container

| Endpoint | What it proves |
|---|---|
| `http://127.0.0.1:7860/` | Gradio UI is up |
| `127.0.0.1:50051` | OpenClaude DO daemon (TCP-bound, no HTTP) |
| `127.0.0.1:50052` | OpenClaude OR daemon (only if `OPENROUTER_API_KEY` is set) |
| `127.0.0.1:9377` | Camofox browser server |
| `127.0.0.1:8765` | OpenClaw HTTP gateway (defaults ON) |
| `127.0.0.1:7862` | Mythos FastAPI plane (only if `MYTHOS_API=1`) |

---

## 9. Cost-control tips (DO Serverless Inference)

- **Set a hard budget** in your DO billing dashboard. The container honours `RHODAWK_HARD_BUDGET_USD` if you set it in `.env`; the architect router will pin every call to TIER 5 once it's exceeded.
- The **TRIAGE** role (`qwen3-32b`) is *much* cheaper than EXECUTION; the router uses it automatically for filtering steps.
- `RECON_MODEL=kimi-k2.5` and the `FALLBACK_MODEL` family are **OpenRouter only** — they will not bill DO.

---

## 10. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Container exits immediately, log says `Required secret 'GITHUB_TOKEN' is not set` | `.env` not loaded | Confirm `env_file: .env` in compose; rerun `docker compose up -d`. |
| `No inference provider key found` | Both DO and OR keys missing | Set at least `DO_INFERENCE_API_KEY` in `.env`. |
| Gradio UI loads but every action returns *"all tier-X models unavailable"* | DO key invalid or model id wrong | `docker compose exec rhodawk python -c "from llm_router import chat_text; print(chat_text('TRIAGE','ping'))"` to see the underlying HTTP error. |
| `openclaude-or.log` says `skipping or daemon — no API key` | Expected when only DO is set | No action needed; the OR daemon is optional. |
| Port 7860 already in use | Another process owns it | Set `HOST_PORT=7870` in `.env`, then `docker compose up -d`. |
| Camofox keeps restarting | First-run engine download (~300 MB) | Wait 2–3 minutes; check `/tmp/camofox.log` inside the container. |

---

## 11. Updating the Model Squad without rebuilding

Every role is overridable through env. Example: pin EXECUTION to a smaller, cheaper DO model and HERMES to a larger one:

```bash
echo 'EXECUTION_MODEL=qwen3-32b'                     >> .env
echo 'HERMES_MODEL=llama-3.3-70b-instruct'           >> .env
docker compose restart rhodawk
```

The container re-reads `.env` on restart; no rebuild required.

---

That's it. You now have a self-contained DevSecOps engine running autonomously on your VPS, with DigitalOcean Serverless Inference as the primary brain and OpenRouter as the safety net.
