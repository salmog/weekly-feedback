# Ubuntu Server Deployment

## What to transfer

Transfer the entire project directory **except** these (they get rebuilt on the server):

```
EXCLUDE:
  .venv/              # rebuilt on server
  data/               # rebuilt on server (or transfer if you want existing data)
  __pycache__/        # auto-generated
  *.egg-info/         # auto-generated
  .env                # create on server with production values
  weekly              # SSH private key — do NOT transfer
  weekly.pub          # SSH public key — do NOT transfer
  weekly-feedback/    # git metadata — not needed on server
```

### Transfer via SFTP (Termius)

Connect to your Ubuntu server in Termius and upload to `/opt/trading-research/` (or wherever you prefer):

```
Files/directories to upload:
  src/
  scripts/
  tests/
  pyproject.toml
  .env.example
  .gitignore
  Dockerfile
  docker-compose.yml
  CLAUDE.md
  DEPLOY.md
```

## Setup on Ubuntu (without Docker)

```bash
# 1. Install Python 3.12
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3.12-dev

# 2. Go to project directory
cd /opt/trading-research

# 3. Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# 4. Install dependencies
pip install -e ".[dev]"

# 5. Create .env from example and edit for production
cp .env.example .env
```

Edit `.env` for production:
```bash
WEEKLY_ENV=production
WEEKLY_DATA_DIR=/opt/trading-research/data
WEEKLY_SQLITE_URL=sqlite:////opt/trading-research/data/metadata.sqlite
WEEKLY_DUCKDB_PATH=/opt/trading-research/data/analytics.duckdb
WEEKLY_LOG_LEVEL=INFO
WEEKLY_LOG_FORMAT=json
WEEKLY_FASTAPI_HOST=0.0.0.0
WEEKLY_FASTAPI_PORT=8000
```

```bash
# 6. Create data directory
mkdir -p data/debug_csv

# 7. Seed tickers
python3.12 scripts/seed_universe.py

# 8. Run initial backfill (takes a while for 500 tickers)
python3.12 scripts/backfill.py

# 9. Start the server
uvicorn weekly.main:app --host 0.0.0.0 --port 8000
```

## Setup on Ubuntu (with Docker)

```bash
# 1. Install Docker
sudo apt update
sudo apt install -y docker.io docker-compose-v2
sudo systemctl enable docker

# 2. Go to project directory
cd /opt/trading-research

# 3. Create .env from example
cp .env.example .env
# Edit .env for production (see above)

# 4. Build and start
docker compose up -d

# 5. Seed tickers (inside container)
docker compose exec app python3.12 scripts/seed_universe.py

# 6. Run backfill (inside container)
docker compose exec app python3.12 scripts/backfill.py
```

## Run as a systemd service (without Docker)

Create `/etc/systemd/system/trading-research.service`:

```ini
[Unit]
Description=Trading Research Platform
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/trading-research
ExecStart=/opt/trading-research/.venv/bin/uvicorn weekly.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
EnvironmentFile=/opt/trading-research/.env

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable trading-research
sudo systemctl start trading-research

# Check status
sudo systemctl status trading-research

# View logs
journalctl -u trading-research -f
```

## Updating the server

After pushing changes to GitHub:

```bash
cd /opt/trading-research
git pull
source .venv/bin/activate
pip install -e .
sudo systemctl restart trading-research
```

Or with Docker:
```bash
cd /opt/trading-research
git pull
docker compose up -d --build
```
