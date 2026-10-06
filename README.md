# AuraStay

A rental marketplace and agency workspace. Guests browse properties and pay a small reservation fee. Agencies manage properties, reservations, check-ins, commissions, teams and expenses.

## Layout

| Path | What it is |
| --- | --- |
| `frontend/` | React app (Create React App + craco, Tailwind). Public marketplace and the `/workspace` agency area. |
| `backend/` | FastAPI API on MongoDB (`server.py` is the entry point), with tests in `backend/tests/`. |
| `checkin-kit/` | A standalone check-in pass studio and QR check-in desk backed by a Google Sheet. It is served at `/pass/` on the Vercel deployment. See `checkin-kit/README.md`. |
| `docs/` | The product brief (`PRD.md`), the build plan and the design guidelines. |

## Run locally

**With Docker (easiest).** Install [Docker Desktop](https://www.docker.com/products/docker-desktop/), then from the repo folder run:

```bash
docker compose up --build
```

- Marketplace: http://localhost:3000
- Agency workspace: http://localhost:3000/login. Sign in as `owner@aurastay.com` / `owner1234` (platform owner) or `manager@aurastay.com` / `manager1234` (agency manager).
- Check-in kit: http://localhost:3000/pass/ (desk at `/pass/checkin/`)
- API: http://localhost:8000/api/health

Data is kept in a Docker volume between runs. To change the logins or secrets, put them in a `.env` file next to `docker-compose.yml` before the first run. Stop with `Ctrl+C`, and wipe the data with `docker compose down -v`.

**Without Docker** (for example on an older Mac). Install [Python 3](https://www.python.org/downloads/macos/) and [Node.js](https://nodejs.org). For the database, create a free cluster on [MongoDB Atlas](https://www.mongodb.com/cloud/atlas/register), or run MongoDB locally. Then run:

```bash
./run-local.sh
```

On the first run it asks for your MongoDB connection string and saves it, with the logins above, in `backend/.env`. It then installs everything and opens http://localhost:3000.

Or start each part by hand:

```bash
# API
cd backend
pip install -r requirements.txt
MONGO_URL=mongodb://localhost:27017 DB_NAME=aurastay JWT_SECRET=dev \
BOOTSTRAP_EMAIL=owner@aurastay.com BOOTSTRAP_PASSWORD=owner1234 \
MANAGER_EMAIL=manager@aurastay.com MANAGER_PASSWORD=manager1234 \
uvicorn server:app --port 8000

# Web app (second terminal)
cd frontend
yarn install
REACT_APP_BACKEND_URL=http://localhost:8000 yarn start
```

## Configuration

**Backend:**
- `MONGO_URL`, `DB_NAME`, `JWT_SECRET`, `CORS_ORIGINS`
- `PUBLIC_APP_URL`, `CHECKIN_SECRET` for check-in pass links
- `BOOTSTRAP_EMAIL`/`BOOTSTRAP_PASSWORD` and `MANAGER_EMAIL`/`MANAGER_PASSWORD` for seed accounts
- `EMERGENT_LLM_KEY` and `INTEGRATION_PROXY_URL` (optional) for hosted media uploads. Without them, uploads are stored locally.

**Frontend:** `REACT_APP_BACKEND_URL`, the API base URL.

## Deploy

- **Frontend:** Vercel. Set the root directory to the repo root (uses `vercel.json`) or to `frontend/` (uses `frontend/vercel.json`). `yarn build` copies `checkin-kit/` to `/pass`.
- **Backend:** Railway, using `railway.json` and `backend/Dockerfile`.
- **CI:** `.github/workflows/deploy.yml` builds both Docker images on every push and PR.
