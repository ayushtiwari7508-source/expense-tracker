#!/usr/bin/env bash
# Frontend E2E checks: dev-server compile, page routes, CORS preflight.
# Set E2E_API_URL to point the CORS checks at a running API (default localhost:8000).
set -u
cd "$(dirname "$0")/../frontend"   # this repo IS the frontend

API_BASE="${E2E_API_URL:-http://localhost:8000/api/v1}"
LOG=/tmp/et-fe-dev.log
PASS=0; FAIL=0
check() {
  if [[ "$2" == "$3" ]]; then PASS=$((PASS+1)); echo "PASS: $1";
  else FAIL=$((FAIL+1)); echo "FAIL: $1 (expected [$2] got [$3])"; fi
}

cleanup() { [[ -n "${DEV_PID:-}" ]] && kill "$DEV_PID" 2>/dev/null; }
trap cleanup EXIT

rm -f "$LOG"
npm run dev > "$LOG" 2>&1 &
DEV_PID=$!

# Wait for the server to accept requests (Next dev compiles lazily per route).
ok=1
for _ in $(seq 1 120); do
  curl -sf -o /dev/null http://localhost:3000/ && { ok=0; break; }
  sleep 0.5
done
check "dev server responds" 0 "$ok"

fetch_code() { curl -s -o /dev/null -w '%{http_code}' "$1"; }

check "landing / 200"        200 "$(fetch_code http://localhost:3000/)"
check "/login 200"           200 "$(fetch_code http://localhost:3000/login)"
check "/register 200"        200 "$(fetch_code http://localhost:3000/register)"
check "/dashboard 200"       200 "$(fetch_code http://localhost:3000/dashboard)"
check "/expenses 200"        200 "$(fetch_code http://localhost:3000/expenses)"
check "/budgets 200"         200 "$(fetch_code http://localhost:3000/budgets)"
check "/alerts 200"          200 "$(fetch_code http://localhost:3000/alerts)"
check "/analytics 200"       200 "$(fetch_code http://localhost:3000/analytics)"
check "/settings 200"        200 "$(fetch_code http://localhost:3000/settings)"

# Landing page actually renders the app shell (not an error page).
curl -s http://localhost:3000/ | grep -q "Expense Tracker" \
  && check "landing renders app title" 0 0 || check "landing renders app title" 0 1

# CORS preflight from the browser origin must be accepted by FastAPI.
CORS=$(curl -s -o /dev/null -w '%{http_code}' -X OPTIONS "$API_BASE/auth/login" \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type")
check "CORS preflight 200/204" 0 "$( [[ "$CORS" == 200 || "$CORS" == 204 ]] && echo 0 || echo 1 )"

ALLOW=$(curl -s -D - -o /dev/null -X OPTIONS "$API_BASE/auth/login" \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: POST" \
  | tr -d '\r' | grep -i '^access-control-allow-origin' | awk '{print $2}')
check "allow-origin echoes browser origin" "http://localhost:3000" "$ALLOW"

# Compile health: dev log must not contain build errors.
sleep 2
if grep -qE "Failed to compile|Error:" "$LOG"; then
  check "no compile errors in dev log" 0 1
  grep -E "Failed to compile|Error:" "$LOG" | head -5
else
  check "no compile errors in dev log" 0 0
fi

echo
echo "RESULT: PASS=$PASS FAIL=$FAIL"
[[ $FAIL -eq 0 ]]
