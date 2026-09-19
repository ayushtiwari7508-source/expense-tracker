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

No backend secrets live in this app — the browser holds only the JWT access
token it receives at login.

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
