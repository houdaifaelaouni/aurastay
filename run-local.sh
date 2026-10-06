#!/usr/bin/env bash
# Runs AuraStay on this computer without Docker.
#   ./run-local.sh
# Needs Python 3 and Node.js. The database is MongoDB: either a free MongoDB
# Atlas cluster (paste its connection string when asked) or a local MongoDB.
# Then open http://localhost:3000 — stop everything with Ctrl+C.
set -euo pipefail
cd "$(dirname "$0")"

say() { printf '\n\033[1m%s\033[0m\n' "$*"; }
fail() { printf '\n\033[31m%s\033[0m\n' "$*"; exit 1; }

command -v python3 >/dev/null || fail "Python 3 is missing. Install it from https://www.python.org/downloads/macos/ and run this again."
command -v node >/dev/null || fail "Node.js is missing. Install the LTS version from https://nodejs.org and run this again."

# Settings live in backend/.env (the API reads it on start). Created once.
ENV_FILE=backend/.env
if [ ! -f "$ENV_FILE" ]; then
  say "First run: where is your database?"
  echo "Paste your MongoDB connection string (from MongoDB Atlas › Connect › Drivers),"
  echo "or press Enter to use a MongoDB running on this computer."
  read -r -p "> " MONGO
  MONGO=${MONGO:-mongodb://localhost:27017}
  SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
  cat > "$ENV_FILE" <<EOF
MONGO_URL=$MONGO
DB_NAME=aurastay
JWT_SECRET=$SECRET
CORS_ORIGINS=http://localhost:3000
PUBLIC_APP_URL=http://localhost:3000
CHECKIN_SECRET=$SECRET
BOOTSTRAP_EMAIL=owner@aurastay.com
BOOTSTRAP_PASSWORD=owner1234
MANAGER_EMAIL=manager@aurastay.com
MANAGER_PASSWORD=manager1234
EOF
  echo "Saved to $ENV_FILE. Edit it any time to change the database or logins."
fi

say "Installing the API (first run takes a few minutes)…"
[ -d backend/.venv ] || python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install -q --upgrade pip
backend/.venv/bin/python -m pip install -q -r backend/requirements.txt

say "Building the website…"
YARN="npx --yes yarn@1.22.22"
(cd frontend && $YARN install --frozen-lockfile --silent && REACT_APP_BACKEND_URL=http://localhost:8000 $YARN build)

say "Starting AuraStay…"
(cd backend && exec .venv/bin/python -m uvicorn server:app --host 127.0.0.1 --port 8000) &
API=$!
(cd frontend && exec npx --yes serve@14 build -l 3000 --no-clipboard) &
WEB=$!
trap 'kill $API $WEB 2>/dev/null; exit 0' INT TERM

for _ in $(seq 1 30); do
  kill -0 $API 2>/dev/null || { kill $WEB 2>/dev/null; fail "The API stopped. Check the error above (often the MongoDB address in $ENV_FILE)."; }
  python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health')" 2>/dev/null && break
  sleep 2
done
cat <<'EOF'

  AuraStay is running.
    Marketplace:   http://localhost:3000
    Workspace:     http://localhost:3000/login  (owner@aurastay.com / owner1234)
    Check-in kit:  http://localhost:3000/pass/
  Press Ctrl+C to stop.
EOF
command -v open >/dev/null && open http://localhost:3000 || true
wait
