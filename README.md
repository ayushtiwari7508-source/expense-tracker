# Expense Tracker

Full-stack expense tracking with analytics: a Next.js + TypeScript frontend, a
FastAPI + SQLAlchemy backend, and PostgreSQL — with a Pandas/NumPy analytics
engine (aggregation, heap-based top-N, time-series trends) running entirely on
the backend.

## Architecture

```
Browser
   ↓
Next.js (:3000)          REST/JSON, JWT bearer auth
   ↓
FastAPI (:8000)          routes → services → analytics
   ↓
SQLAlchemy (async)
   ↓
PostgreSQL (:5432)       Alembic-managed schema
```

- **Frontend** — `frontend/` — Next.js 14 App Router, Tailwind, ECharts. The
  browser calls the API directly; the API base URL is `NEXT_PUBLIC_API_URL`.
- **Backend** — `backend/` — FastAPI, Pydantic v2, JWT auth (Argon2 hashing),
  Decimal money handling end to end.
- **Analytics** — `backend/app/analytics/` — aggregation, `heapq` top-N,
  time-series trends & moving averages, insights. All numbers shown in the UI
  are computed here.
- **Migrations** — Alembic only. `Base.metadata.create_all()` is never used for
  schema management.

## Technology stack

| Layer     | Technology |
|-----------|------------|
| Frontend  | Next.js 14, React 18, TypeScript, Tailwind CSS, ECharts 6, lucide-react |
| Backend   | Python 3.11+ (3.13 tested), FastAPI, Pydantic v2, SQLAlchemy 2 async |
| Database  | PostgreSQL 16 (psycopg 3) |
| Analytics | Pandas, NumPy, statsmodels |
| Auth      | JWT (PyJWT), Argon2 (`pwdlib`) |
| Tests     | pytest + HTTPX (real PostgreSQL), bash E2E suites in `scripts/` |
| Infra     | Docker multi-stage builds, Docker Compose, GitHub Actions |

## Prerequisites

- Docker + Docker Compose (recommended path)
- Python 3.11+ and Node 22 (for local development outside Docker)
- A PostgreSQL instance for local dev (the compose `db` service works)

## Quick start with Docker (production-like)

```bash
# 1. Configure environment
cp .env.example .env
#    → set JWT_SECRET_KEY (openssl rand -hex 32); adjust CORS/DB if needed

# 2. Build and start the whole stack
docker compose up -d --build

# 3. Verify
curl http://localhost:8000/api/v1/health          # backend
curl http://localhost:8000/api/v1/health/db       # database readiness
curl http://localhost:3000/api-health             # frontend liveness
open http://localhost:3000                        # application
```

On startup the backend container waits for PostgreSQL, runs
`alembic upgrade head`, then serves with uvicorn on `0.0.0.0:$PORT`.

Useful commands:

```bash
docker compose ps                 # status + health
docker compose logs -f api        # backend logs
docker compose down               # stop (keeps the postgres_data volume)
docker compose up -d --build api  # rebuild one service
```

> Do **not** use `docker compose down -v` casually — it deletes the database
> volume.

## Local development (without Docker for app code)

```bash
# 1. Database only
docker compose up -d db

# 2. Backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
pip install -e .                       # makes `backend.app.*` importable
cp backend/.env.example backend/.env   # then edit secrets

cd backend && alembic upgrade head && cd ..

uvicorn backend.app.main:app --reload --port 8000

# 3. Frontend (another terminal)
cd frontend
npm ci
#    NEXT_PUBLIC_API_URL defaults to http://localhost:8000/api/v1;
#    to override, create frontend/.env.local with:
#      NEXT_PUBLIC_API_URL=http://your-api-url/api/v1
npm run dev
```

- Swagger UI: http://localhost:8000/docs
- Health: http://localhost:8000/api/v1/health · DB readiness:
  http://localhost:8000/api/v1/health/db

## Environment variables

Copy `.env.example` (root) for Docker Compose, and `backend/.env.example` for
local backend development. Never commit real `.env` files.

| Variable | Where | Secret | Notes |
|---|---|---|---|
| `JWT_SECRET_KEY` | backend / root `.env` | **yes** | required by compose (`:?` guard) |
| `DATABASE_URL` | backend | **yes** | `postgresql+psycopg://user:pass@host:5432/db` |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | root `.env` | **yes** | compose `db` service |
| `CORS_ORIGINS` | backend / root `.env` | no | comma-separated frontend origins |
| `JWT_ALGORITHM` | backend | no | default `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | backend | no | default `30` |
| `APP_ENV` / `DEBUG` | backend | no | production: `APP_ENV=production`, `DEBUG=false` |
| `PORT` | backend container | no | uvicorn binds `0.0.0.0:$PORT` (default 8000) |
| `JWT_COOKIE_NAME` | backend | no | default `access_token` |
| `JWT_COOKIE_SECURE` | backend | no | unset = auto (`true` when `APP_ENV=production`) |
| `JWT_COOKIE_HTTP_ONLY` | backend | no | default `true` — do not disable |
| `JWT_COOKIE_SAMESITE` | backend | no | `lax` (default) \| `strict` \| `none` |
| `JWT_COOKIE_PATH` | backend | no | default `/` |
| `JWT_COOKIE_DOMAIN` | backend | no | unset = host-only; set only for sibling-subdomain deployments |
| `NEXT_PUBLIC_API_URL` | frontend **build arg** | no | baked at build time; must be browser-reachable |

`NEXT_PUBLIC_*` variables are inlined into the client bundle at **build** time —
changing the API URL requires rebuilding the frontend image. No backend secrets
are ever exposed to the frontend.

## Authentication & security

**The JWT is stored in an HttpOnly cookie and is never exposed to JavaScript.**
An XSS vulnerability cannot read the token, and the frontend contains no token
storage, no `Authorization` header construction, and no `localStorage` JWT.

```
Login → FastAPI validates credentials → JWT → Set-Cookie (HttpOnly)
Browser attaches cookie automatically → FastAPI extracts & validates JWT
Logout → server clears cookie → /auth/me returns 401
```

- **HttpOnly** — always `true`; JavaScript cannot read the cookie.
- **Secure** — `true` when `APP_ENV=production` (auto, or force via
  `JWT_COOKIE_SECURE`). Never disabled in real production deployments.
- **SameSite** — `lax` by default. The deployed architecture is same-site
  (Next.js and FastAPI behind one origin / `localhost` ports in dev), so `lax`
  blocks cross-site CSRF while keeping normal navigation working. Cross-site
  subdomain deployments would need `none` **plus** a CSRF token strategy.
- **CSRF strategy** — the `SameSite=Lax` cookie is the primary defense: cross-
  site pages cannot trigger authenticated POST/PATCH/DELETE with cookies, and
  all state-changing endpoints are JSON-only (never form-encoded), which
  cross-origin forms cannot produce without a CORS grant. A double-submit CSRF
  token would only become necessary with a cross-site cookie deployment.
- **CORS** — `allow_credentials=True` with an **explicit origin allowlist**
  (`CORS_ORIGINS`); wildcard `*` is never used with credentials.
- **Bearer fallback** — the auth dependency still accepts an explicit
  `Authorization: Bearer` header (explicit headers win over the cookie) so
  scripts/CI clients keep working; the browser uses only the cookie.
- **API security headers** — `X-Content-Type-Options: nosniff`,
  `Referrer-Policy: same-origin`, and a restrictive `Content-Security-Policy`
  (`default-src 'none'; frame-ancestors 'none'`) are set on API responses; the
  API serves JSON only, so this cannot break the Next.js frontend or ECharts.
- **Passwords** — Argon2id hashed (never returned by any endpoint); the JWT
  secret is server-side only (`JWT_SECRET_KEY`), never in frontend code or
  `NEXT_PUBLIC_*` variables.

## Database setup & migrations

```bash
# Apply all migrations (local dev or against any DATABASE_URL)
cd backend
DATABASE_URL=postgresql+psycopg://... alembic upgrade head

# Check current revision
alembic current

# Roll back one revision (test environments only)
alembic downgrade -1
```

The backend container applies migrations automatically before serving. With
multiple backend replicas, run migrations as a separate one-off step instead of
letting every replica race to `upgrade head`.

## Testing

**Backend** (152 tests, real PostgreSQL, per-test transaction rollback):

```bash
# One-time: create the dedicated test database
docker exec expense-tracker-db psql -U postgres -c "CREATE DATABASE expense_tracker_test;"

# From the project root
pytest -v
```

The suite uses `TEST_DATABASE_URL` (see `backend/.env.example`). SQLite fallback
exists but has reduced fidelity (no native UUID/NUMERIC/CHECK enforcement).

**API E2E** (boots its own server, or point it at the compose stack):

```bash
./scripts/e2e_api_tests.sh                                      # self-contained
E2E_BASE_URL=http://localhost:8000/api/v1 ./scripts/e2e_api_tests.sh   # against compose
```

**Frontend checks** (routes, compile, CORS against the API):

```bash
E2E_API_URL=http://localhost:8000/api/v1 ./scripts/e2e_frontend_checks.sh
```

**Frontend lint + production build:**

```bash
cd frontend && npm run lint && npm run build
```

## Production build

- **Backend image** — `backend/Dockerfile`: multi-stage, python:3.13-slim,
  wheels-only runtime, non-root user, Python-stdlib healthcheck on
  `/api/v1/health`.
- **Frontend image** — `frontend/Dockerfile`: multi-stage, `output: "standalone"`
  Next.js build, minimal runtime (server.js + traced deps), non-root user,
  healthcheck on `/api-health`.
- **Compose** — three services with real healthchecks; `api` waits for `db`
  readiness, `frontend` waits for `api` health. Postgres is published on
  `127.0.0.1:5432` only (loopback) — the API reaches it over the internal
  Docker network.

## Deployment architecture

Target: **Vercel** (frontend) · **Render or Railway** (backend) · **managed
PostgreSQL** (e.g. Neon/Render DB/Railway Postgres).

- Frontend → deploy `frontend/` to Vercel. Set `NEXT_PUBLIC_API_URL` to the
  public backend URL (`https://api.example.com/api/v1`), **not** a Docker
  internal hostname. Rebuild triggers on push.
- Backend → deploy `backend/` with the provided Dockerfile. The image honors
  `PORT` (binds `0.0.0.0:$PORT`), reads `DATABASE_URL`, `JWT_SECRET_KEY`,
  `CORS_ORIGINS` from the platform's environment. Set `CORS_ORIGINS` to the
  exact Vercel origin(s). Run migrations (`alembic upgrade head`) as a release
  step or one-off job — not from every replica.
- Database → managed PostgreSQL; set `DATABASE_URL` in the backend provider's
  secret store. Never use the local Docker database in production.

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| API container restarts with `exec: "./entrypoint.sh": permission denied` | Rebuild after `chmod +x backend/entrypoint.sh` (the Dockerfile also enforces this). |
| `db not ready: failed to resolve host ...` | `DATABASE_URL` host is wrong — inside compose the host must be `db`, not `localhost`. |
| Compose refuses to start API: `set JWT_SECRET_KEY in .env` | Root `.env` missing or `JWT_SECRET_KEY` empty — copy `.env.example` and set it. |
| Frontend builds but API calls fail from the browser | `NEXT_PUBLIC_API_URL` baked at build time is wrong or unreachable from the browser; rebuild with the correct public URL. |
| CORS errors in the browser console | Backend `CORS_ORIGINS` must list the exact frontend origin (scheme + host + port). |
| Migrations vs pytest conflict | pytest bootstraps its schema in the test DB; run Alembic against the dev DB or a clean schema, not a post-pytest test DB. |
| Health `{"database":"unavailable"}` | DB down/unreachable; `/api/v1/health/db` reports readiness, the pool reconnects once the DB returns. |

## CI

`.github/workflows/ci.yml` runs on push/PR:

1. **Backend** — pip install, `pip install -e .`, Alembic against a service
   PostgreSQL, full pytest suite.
2. **Frontend** — `npm ci`, lint, production build.
3. **Docker** — build both images (backend + frontend with build args).

Failures fail the pipeline; no `|| true`, no suppressed errors.

## License

[MIT](LICENSE) © Ayush Tiwari
