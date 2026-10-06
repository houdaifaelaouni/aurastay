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

```bash
# Backend (needs MongoDB)
cd backend
pip install -r requirements.txt
MONGO_URL=mongodb://localhost:27017 DB_NAME=aurastay JWT_SECRET=dev uvicorn server:app --reload --port 8000

# Frontend
cd frontend
yarn install
REACT_APP_BACKEND_URL=http://localhost:8000 yarn dev
```

Or run both with `docker compose up`.

## Configuration

**Backend:**
- `MONGO_URL`, `DB_NAME`, `JWT_SECRET`, `CORS_ORIGINS`
- `PUBLIC_APP_URL`, `CHECKIN_SECRET` for check-in pass links
- `BOOTSTRAP_EMAIL`/`BOOTSTRAP_PASSWORD` and `MANAGER_EMAIL`/`MANAGER_PASSWORD` for seed accounts
- `EMERGENT_LLM_KEY` and `INTEGRATION_PROXY_URL` (optional) for hosted media uploads. Without them, uploads are stored locally.

**Frontend:** `REACT_APP_BACKEND_URL`, the API base URL.

## Deploy

- **Frontend:** Vercel, using `vercel.json` at the repo root. It builds `frontend/` and copies `checkin-kit/` to `/pass`.
- **Backend:** Railway, using `railway.json` and `backend/Dockerfile`.
- **CI:** `.github/workflows/deploy.yml` builds both Docker images on every push and PR.
