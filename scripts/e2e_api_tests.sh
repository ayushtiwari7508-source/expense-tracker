#!/usr/bin/env bash
# End-to-end API verification for the Expense Tracker backend.
# Boots its own uvicorn instance, runs assertions, then shuts it down.
set -u
cd "$(dirname "$0")/.."   # project root

PORT=8123
# Default: boot a local uvicorn on $PORT. With E2E_BASE_URL set, test an
# already-running server (e.g. the dockerized API) instead of starting one.
if [[ -n "${E2E_BASE_URL:-}" ]]; then
  BASE="${E2E_BASE_URL%/}"
else
  BASE="http://localhost:$PORT/api/v1"
fi
PASS=0; FAIL=0; LOG=/tmp/et-e2e-uvicorn.log

cleanup() { [[ -n "${SERVER_PID:-}" ]] && kill "$SERVER_PID" 2>/dev/null; }
trap cleanup EXIT

start_server() {
  if [[ -n "${E2E_BASE_URL:-}" ]]; then
    return 0   # external server (e.g. dockerized API); nothing to boot
  fi
  .venv/bin/uvicorn backend.app.main:app --port "$PORT" > "$LOG" 2>&1 &
  SERVER_PID=$!
  for _ in $(seq 1 40); do
    curl -sf "$BASE/health" >/dev/null 2>&1 && return 0
    sleep 0.25
  done
  echo "SERVER FAILED TO START"; tail -20 "$LOG"; exit 1
}

# check <name> <expected> <actual>
check() {
  if [[ "$2" == "$3" ]]; then PASS=$((PASS+1)); echo "PASS: $1";
  else FAIL=$((FAIL+1)); echo "FAIL: $1 (expected [$2] got [$3])"; fi
}

# method url [data] [token] -> sets STATUS and BODY
req() {
  local m=$1 u=$2 d=${3:-} t=${4:-}
  local args=(-s -w $'\n%{http_code}' -X "$m" "$u" -H 'Content-Type: application/json')
  [[ -n "$t" ]] && args+=(-H "Authorization: Bearer $t")
  [[ -n "$d" ]] && args+=(-d "$d")
  local out; out=$(curl "${args[@]}")
  STATUS=$(echo "$out" | tail -1)
  BODY=$(echo "$out" | sed '$d')
}

start_server
TODAY=$(date +%F)
SUFFIX=$RANDOM$RANDOM   # unique mailbox per run so re-runs never hit 409
UA_EMAIL="usera$SUFFIX@e2etest.dev"
UB_EMAIL="userb$SUFFIX@e2etest.dev"

echo "=== AUTH ==="
req POST "$BASE/auth/register" '{"name":"User A","email":"'"$UA_EMAIL"'","password":"Passw0rdA"}'
check "register 201" 201 "$STATUS"; [[ "$STATUS" == "201" ]] && UA_ID=$(echo "$BODY" | jq -r .id)
echo "$BODY" | jq -e 'has("password_hash") | not' >/dev/null && check "no password_hash leaked" 0 $? || check "no password_hash leaked" 0 1

req POST "$BASE/auth/login" '{"email":"'"$UA_EMAIL"'","password":"Passw0rdA"}'
check "login 200" 200 "$STATUS"; TA=$(echo "$BODY" | jq -r .access_token)

req POST "$BASE/auth/login" '{"email":"'"$UA_EMAIL"'","password":"WrongPass1"}'
check "wrong password 401" 401 "$STATUS"

req POST "$BASE/auth/register" '{"name":"Dup","email":"'"$UA_EMAIL"'","password":"Passw0rdA"}'
check "duplicate email 409" 409 "$STATUS"

req GET "$BASE/auth/me" "" ""
check "no token 401" 401 "$STATUS"
req GET "$BASE/auth/me" "" "invalid.token.here"
check "invalid token 401" 401 "$STATUS"
req GET "$BASE/auth/me" "" "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjMifQ.sig"
check "garbage signed token 401" 401 "$STATUS"
req GET "$BASE/auth/me" "" "$TA"
check "me 200 with token" 200 "$STATUS"
echo "$BODY" | jq -e '.email=="'"$UA_EMAIL"'"' >/dev/null && check "me returns profile" 0 $? || check "me returns profile" 0 1

# Expired token: craft a token signed with the real secret but expired in the past
EXPIRED=$(.venv/bin/python - <<'PYEOF'
from backend.app.core.config import settings
import jwt, time
print(jwt.encode({"sub": "00000000-0000-0000-0000-000000000000", "iat": int(time.time()) - 7200, "exp": int(time.time()) - 3600, "type": "access"}, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM))
PYEOF
)
[[ -n "$EXPIRED" ]] || { echo "FAIL: could not craft expired token"; exit 1; }
req GET "$BASE/auth/me" "" "$EXPIRED"
check "expired token 401" 401 "$STATUS"

echo "=== USER ISOLATION (User B) ==="
req POST "$BASE/auth/register" '{"name":"User B","email":"'"$UB_EMAIL"'","password":"Passw0rdB"}'
check "register B 201" 201 "$STATUS"; [[ "$STATUS" == "201" ]] && UB_ID=$(echo "$BODY" | jq -r .id)
req POST "$BASE/auth/login" '{"email":"'"$UB_EMAIL"'","password":"Passw0rdB"}'
TB=$(echo "$BODY" | jq -r .access_token)

req POST "$BASE/expenses" '{"amount":"120.50","category":"Food","description":"A lunch","payment_method":"UPI","expense_date":"'"$TODAY"'"}' "$TA"
check "A creates expense 201" 201 "$STATUS"; EA_ID=$(echo "$BODY" | jq -r .id)
req POST "$BASE/expenses" '{"amount":"777.00","category":"Travel","description":"B cab","payment_method":"Cash","expense_date":"'"$TODAY"'"}' "$TB"
check "B creates expense 201" 201 "$STATUS"; EB_ID=$(echo "$BODY" | jq -r .id)

req GET "$BASE/expenses/$EB_ID" "" "$TA"
check "A cannot read B expense (404)" 404 "$STATUS"
req PATCH "$BASE/expenses/$EB_ID" '{"amount":"1.00"}' "$TA"
check "A cannot update B expense (404)" 404 "$STATUS"
req DELETE "$BASE/expenses/$EB_ID" "" "$TA"
check "A cannot delete B expense (404)" 404 "$STATUS"
req GET "$BASE/expenses" "" "$TA"
check "A list has only own expense" 1 "$(echo "$BODY" | jq '.items | length')"
check "A list total=1" 1 "$(echo "$BODY" | jq '.total')"

echo "=== EXPENSE CRUD + FILTERS ==="
req POST "$BASE/expenses" '{"amount":"0","category":"Food","expense_date":"'"$TODAY"'","payment_method":"UPI"}' "$TA"
check "zero amount 422" 422 "$STATUS"
req POST "$BASE/expenses" '{"amount":"10","category":"Nope","expense_date":"'"$TODAY"'","payment_method":"UPI"}' "$TA"
check "bad category 422" 422 "$STATUS"
req POST "$BASE/expenses" '{"amount":"10","category":"Food","expense_date":"'"$TODAY"'","payment_method":"CarrierPigeon"}' "$TA"
check "bad payment method 422" 422 "$STATUS"
req POST "$BASE/expenses" '{"amount":"-5","category":"Food","expense_date":"'"$TODAY"'","payment_method":"UPI"}' "$TA"
check "negative amount 422" 422 "$STATUS"
req POST "$BASE/expenses" '{"amount":"10.999","category":"Food","expense_date":"'"$TODAY"'","payment_method":"UPI"}' "$TA"
check ">2dp amount rejected" 422 "$STATUS"

# seed for filters/analytics
req POST "$BASE/expenses" '{"amount":"300.00","category":"Travel","description":"train ticket","payment_method":"Credit Card","expense_date":"2026-09-01"}' "$TA"
check "seed travel 201" 201 "$STATUS"
req POST "$BASE/expenses" '{"amount":"45.25","category":"Food","description":"coffee","payment_method":"Cash","expense_date":"2026-09-02"}' "$TA"
check "seed food 201" 201 "$STATUS"
req POST "$BASE/expenses" '{"amount":"1200.00","category":"Rent","description":"september rent","payment_method":"Bank Transfer","expense_date":"2026-09-05"}' "$TA"
check "seed rent 201" 201 "$STATUS"

req GET "$BASE/expenses?category=Food" "" "$TA"
check "filter category Food -> 2" 2 "$(echo "$BODY" | jq '.total')"
req GET "$BASE/expenses?search=train" "" "$TA"
check "search train -> 1" 1 "$(echo "$BODY" | jq '.total')"
req GET "$BASE/expenses?payment_method=Cash" "" "$TA"
check "filter Cash -> 1" 1 "$(echo "$BODY" | jq '.total')"
req GET "$BASE/expenses?date_from=2026-09-02&date_to=2026-09-05" "" "$TA"
check "date range -> 2" 2 "$(echo "$BODY" | jq '.total')"
req GET "$BASE/expenses?min_amount=300" "" "$TA"
check "min_amount 300 -> 2" 2 "$(echo "$BODY" | jq '.total')"
req GET "$BASE/expenses?sort_by=amount&sort_order=asc&page_size=2" "" "$TA"
check "sort asc first is cheapest" "45.25" "$(echo "$BODY" | jq -r '.items[0].amount')"
check "page_size=2 pages=2" 2 "$(echo "$BODY" | jq '.pages')"
req GET "$BASE/expenses?sort_by=amount;DROP" "" "$TA"
check "sort whitelist 422" 422 "$STATUS"

req PATCH "$BASE/expenses/$EA_ID" '{"amount":"99.99","description":"edited"}' "$TA"
check "update 200" 200 "$STATUS"
check "update persisted amount" "99.99" "$(echo "$BODY" | jq -r .amount)"
req GET "$BASE/expenses/$EA_ID" "" "$TA"
check "get after update" "99.99" "$(echo "$BODY" | jq -r .amount)"
req DELETE "$BASE/expenses/$EA_ID" "" "$TA"
check "delete 204" 204 "$STATUS"
req GET "$BASE/expenses/$EA_ID" "" "$TA"
check "deleted -> 404" 404 "$STATUS"

echo "=== BUDGETS + ALERTS ==="
req POST "$BASE/budgets" '{"category":null,"amount":"500","start_date":"2026-09-01","end_date":"2026-09-30","alert_threshold":"50"}' "$TA"
check "overall budget 201" 201 "$STATUS"; B1=$(echo "$BODY" | jq -r .id)
check "budget spent=1545.25" "1545.25" "$(echo "$BODY" | jq -r .utilization.amount_spent)"
check "budget status EXCEEDED" "EXCEEDED" "$(echo "$BODY" | jq -r .utilization.status)"

req POST "$BASE/budgets" '{"category":"Food","amount":"500","start_date":"2026-09-01","end_date":"2026-09-30","alert_threshold":"60"}' "$TA"
check "category budget 201" 201 "$STATUS"
check "food spent=45.25" "45.25" "$(echo "$BODY" | jq -r .utilization.amount_spent)"
check "food status NORMAL" "NORMAL" "$(echo "$BODY" | jq -r .utilization.status)"
check "food util %" "9.05" "$(echo "$BODY" | jq -r .utilization.utilization_percentage)"

req POST "$BASE/budgets" '{"category":"Food","amount":"100","start_date":"2026-10-01","end_date":"2026-09-01","alert_threshold":50}' "$TA"
check "invalid date range 422" 422 "$STATUS"
req POST "$BASE/budgets" '{"category":"Food","amount":"100","start_date":"2026-09-01","end_date":"2026-09-30","alert_threshold":150}' "$TA"
check "threshold 150 rejected 422" 422 "$STATUS"

req GET "$BASE/alerts" "" "$TA"
check "exceeded alert auto-created" "exceeded" "$(echo "$BODY" | jq -r '.items[0].type')"
check "unread_count=1" 1 "$(echo "$BODY" | jq '.unread_count')"
AL_ID=$(echo "$BODY" | jq -r '.items[0].id')

req PATCH "$BASE/alerts/$AL_ID/read" "" "$TA"
check "mark read 200" 200 "$STATUS"
check "alert now read" "true" "$(echo "$BODY" | jq -r .is_read)"
req GET "$BASE/alerts" "" "$TA"
check "unread_count now 0" 0 "$(echo "$BODY" | jq '.unread_count')"
req PATCH "$BASE/alerts/read-all" "" "$TA"
check "read-all 200" 200 "$STATUS"

# WARNING alert: food spent 45.25, budget 100 → 45.25% < 60? set threshold 40
req POST "$BASE/budgets" '{"category":"Food","amount":"100","start_date":"2026-09-01","end_date":"2026-09-30","alert_threshold":"40"}' "$TA"
check "threshold budget created" 201 "$STATUS"
req GET "$BASE/alerts" "" "$TA"
check "warning alert appears" "warning" "$(echo "$BODY" | jq -r '[.items[] | select(.type=="warning")] | first | .type')"

req GET "$BASE/alerts?unread_only=true" "" "$TB"
check "B sees no A alerts" 0 "$(echo "$BODY" | jq '.items | length')"

echo "=== ANALYTICS ==="
req GET "$BASE/analytics/summary?start_date=2026-09-01&end_date=2026-09-30" "" "$TA"
check "summary total=1545.25" "1545.25" "$(echo "$BODY" | jq -r .total_amount)"
check "summary count=3" 3 "$(echo "$BODY" | jq '.total_expenses')"
check "summary highest=1200.0" "1200.0" "$(echo "$BODY" | jq -r .highest_expense)"
check "summary avg=515.08" "515.08" "$(echo "$BODY" | jq -r .average_expense)"

req GET "$BASE/analytics/categories?start_date=2026-09-01&end_date=2026-09-30" "" "$TA"
check "categories top is Rent" "Rent" "$(echo "$BODY" | jq -r '.[0].category')"
check "rent pct 77.66" "77.66" "$(echo "$BODY" | jq -r '.[0].percentage')"

req GET "$BASE/analytics/trends?granularity=monthly&start_date=2026-09-01&end_date=2026-09-30" "" "$TA"
check "trends monthly 1 point" 1 "$(echo "$BODY" | jq 'length')"
check "trends point total 1545.25" "1545.25" "$(echo "$BODY" | jq -r '.[0].total')"
req GET "$BASE/analytics/trends?granularity=hourly" "" "$TA"
check "bad granularity 422" 422 "$STATUS"

req GET "$BASE/analytics/time-series?granularity=daily&start_date=2026-09-01&end_date=2026-09-05&moving_average_window=3" "" "$TA"
check "time-series 5 zero-filled points" 5 "$(echo "$BODY" | jq '.points | length')"
check "09-02 total 45.25" "45.25" "$(echo "$BODY" | jq -r '.points[] | select(.period=="2026-09-02") | .total')"
check "09-03 zero not invented" "0.0" "$(echo "$BODY" | jq -r '.points[] | select(.period=="2026-09-03") | .total')"
check "has moving_average" "true" "$(echo "$BODY" | jq '.points[-1].moving_average != null')"
check "trend_direction present" "true" "$(echo "$BODY" | jq '.trend_direction | type=="string"')"

req GET "$BASE/analytics/top-expenses?limit=2&start_date=2026-09-01&end_date=2026-09-30" "" "$TA"
check "top limit=2" 2 "$(echo "$BODY" | jq 'length')"
check "top1 is rent 1200" "1200.0" "$(echo "$BODY" | jq -r '.[0].amount')"
check "top2 is travel 300" "300.0" "$(echo "$BODY" | jq -r '.[1].amount')"
check "ranks 1,2" "1,2" "$(echo "$BODY" | jq -r '[.[].rank] | join(",")')"
req GET "$BASE/analytics/top-expenses?limit=0" "" "$TA"
check "limit=0 rejected" 422 "$STATUS"
req GET "$BASE/analytics/top-expenses" "" "$TA"
check "top default 3 for A" 3 "$(echo "$BODY" | jq 'length')"
req GET "$BASE/analytics/top-expenses" "" "$TB"
check "B top expenses isolated" 1 "$(echo "$BODY" | jq 'length')"

req GET "$BASE/analytics/insights?start_date=2026-09-01&end_date=2026-09-30" "" "$TA"
check "insights generated" "true" "$(echo "$BODY" | jq '.insights | length > 0')"
echo "$BODY" | jq -r '.insights[].message' | head -5

req GET "$BASE/analytics/summary" "" ""
check "analytics requires auth" 401 "$STATUS"

echo
echo "RESULT: PASS=$PASS FAIL=$FAIL"
[[ $FAIL -eq 0 ]]
