# Expense Tracker — Frontend

Next.js 14 (App Router) + TypeScript + Tailwind CSS + ECharts client for the
Expense Tracker API. The browser talks to the FastAPI backend directly; all
charts and analytics figures are rendered from API responses.

## Stack

| Concern   | Technology |
|-----------|------------|
| Framework | Next.js 14 App Router, React 18 |
| Language  | TypeScript |
| Styling   | Tailwind CSS |
| Charts    | ECharts 6 |
| Icons     | lucide-react |

## Routes

| Route | Description |
|---|---|
| `/` | Landing page (redirects to login or dashboard) |
| `/login`, `/register` | JWT authentication |
| `/dashboard` | Overview: totals, recent expenses |
| `/expenses` | CRUD list with filters |
| `/budgets` | Budget management with alert thresholds |
| `/alerts` | Budget alert feed |
| `/analytics` | Aggregation, top-N, and time-series charts |
| `/settings` | Profile and password management |
| `/api-health` | Minimal liveness endpoint (container healthcheck target) |

## Environment

`NEXT_PUBLIC_API_URL` is the API base URL and is **baked into the client
bundle at build time**. Changing it requires a rebuild.

```bash
# .env.local for local development (defaults to the compose API)
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

No backend secrets live in this app, and it never sees the JWT: authentication
rides in an HttpOnly cookie attached automatically by the browser
(`credentials: "include"`), so there is no token storage and no `Authorization`
header anywhere in this codebase.

## Development

```bash
npm ci
npm run dev        # http://localhost:3000
```

The API must be running (see the root README for `docker compose up -d db api`
or a local uvicorn setup).

## Production build

```bash
npm run lint
npm run build      # output: "standalone" (server.js + traced deps)
```

The Docker image (`Dockerfile`) is a multi-stage build producing a minimal
non-root runtime with a healthcheck on `/api-health`.

## Checks against a running API

```bash
E2E_API_URL=http://localhost:8000/api/v1 ../scripts/e2e_frontend_checks.sh
```

## End-to-end tests (Playwright)

The suite drives the **real stack** — Chromium → Next.js → FastAPI → a
dedicated PostgreSQL database (`expense_tracker_e2e`) — and covers auth,
expenses (CRUD/search/filter/sort/pagination), budgets, alerts, analytics,
profile, user isolation, empty/error states, responsive layout, and basic
accessibility. Every test registers its own unique user via the real API and
its data is cleaned up afterwards; a console/network audit runs on every test.

One-time setup (create + migrate the E2E database):

```bash
docker exec expense-tracker-db psql -U postgres -c "CREATE DATABASE expense_tracker_e2e;"
cd backend && DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/expense_tracker_e2e" \
  alembic upgrade head
```

Run it (the API must be up; Playwright starts Next.js itself):

```bash
npm run test:e2e          # headless
npm run test:e2e:ui       # interactive UI mode
npm run test:e2e:debug    # debugger
npm run test:e2e:report   # open the HTML report
```

Environment variables: `API_BASE_URL` (default `http://localhost:8000`),
`E2E_BASE_URL` (reuse an already-running frontend instead of the managed
webServer). Reports/traces land in `playwright-report/` and `test-results/`
(both gitignored); CI uploads them on failure and runs the suite on every push.

Tip: to point a locally running `api` container at the E2E database (so tests
can never touch development data), restart it with
`docker compose -f docker-compose.yml -f docker-compose.e2e.yml up -d api`,
and afterwards restore the normal stack with `docker compose up -d --force-recreate api`.
