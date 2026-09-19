"""End-to-end verification against a live API + PostgreSQL.

Usage: python scripts/e2e_verify.py
The script starts uvicorn itself, so no pre-running server is needed.
"""

import subprocess
import sys
import time

import httpx

BASE = "http://127.0.0.1:8000/api/v1"
VENV_BIN = ".venv/bin"


def wait_for_server(timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = httpx.get(f"{BASE}/health", timeout=2.0)
            if r.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(0.5)
    raise RuntimeError("server did not start")


def main() -> None:
    # 1. Start the API server against PostgreSQL.
    server = subprocess.Popen(
        [f"{VENV_BIN}/uvicorn", "backend.app.main:app", "--port", "8000"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        wait_for_server()
        run_checks()
    finally:
        server.terminate()
        server.wait(timeout=10)


def run_checks() -> None:
    ok = 0
    failed = 0

    def check(name: str, cond: bool, extra: str = "") -> None:
        nonlocal ok, failed
        mark = "PASS" if cond else "FAIL"
        if cond:
            ok += 1
        else:
            failed += 1
        print(f"[{mark}] {name}" + (f" — {extra}" if extra else ""))

    # --- Health & docs ---
    r = httpx.get(f"{BASE}/health")
    check("health returns healthy", r.json().get("status") == "healthy")

    r = httpx.get(f"{BASE}/health/db")
    check("health/db verifies PostgreSQL", r.json().get("database") == "connected")

    r = httpx.get("http://127.0.0.1:8000/docs")
    check("docs UI available", r.status_code == 200)

    r = httpx.get("http://127.0.0.1:8000/openapi.json")
    check("openapi schema available", r.status_code == 200)

    # --- Registration & login ---
    email = f"e2e{int(time.time())}@example.com"
    password = "StrongPassword123"

    r = httpx.post(
        f"{BASE}/auth/register",
        json={"name": "Ayush", "email": email, "password": password},
    )
    check("register returns 201", r.status_code == 201)
    body = r.json()
    check("no password_hash in response", "password_hash" not in body)

    r = httpx.post(f"{BASE}/auth/login", json={"email": email, "password": password})
    check("login returns token", r.status_code == 200 and "access_token" in r.json())
    token = r.json()["access_token"]
    H = {"Authorization": f"Bearer {token}"}

    r = httpx.get(f"{BASE}/auth/me", headers=H)
    check("auth/me returns profile", r.status_code == 200 and r.json()["email"] == email)

    # --- Expenses ---
    expenses = [
        {"amount": 250.50, "category": "Food", "description": "Dinner",
         "payment_method": "UPI", "expense_date": "2026-09-16"},
        {"amount": 5000, "category": "Rent", "description": "Monthly rent",
         "payment_method": "Bank Transfer", "expense_date": "2026-09-01"},
        {"amount": 1200, "category": "Shopping", "description": "Clothes",
         "payment_method": "Credit Card", "expense_date": "2026-09-10"},
        {"amount": 80, "category": "Travel", "description": "Taxi",
         "payment_method": "UPI", "expense_date": "2026-09-02"},
    ]
    ids = []
    codes_ok = True
    for e in expenses:
        r = httpx.post(f"{BASE}/expenses", json=e, headers=H)
        codes_ok = codes_ok and r.status_code == 201
        ids.append(r.json()["id"])
    check("create expenses (201)", codes_ok)

    r = httpx.get(f"{BASE}/expenses?category=Food", headers=H)
    check("filter by category", r.json()["total"] == 1)

    r = httpx.get(f"{BASE}/expenses?search=dinner", headers=H)
    check("search 'dinner'", r.json()["total"] == 1)

    r = httpx.get(f"{BASE}/expenses?sort_by=amount&sort_order=desc", headers=H)
    amounts = [i["amount"] for i in r.json()["items"]]
    check("sort by amount desc", amounts == sorted(amounts, reverse=True))

    r = httpx.get(f"{BASE}/expenses?page=1&page_size=2", headers=H)
    body = r.json()
    check("pagination metadata", body["total"] == 4 and len(body["items"]) == 2)

    r = httpx.get(f"{BASE}/expenses/{ids[0]}", headers=H)
    check("get expense by id", r.status_code == 200)

    r = httpx.patch(f"{BASE}/expenses/{ids[3]}", json={"amount": 95}, headers=H)
    check("update expense", r.status_code == 200 and r.json()["amount"] == 95)

    r = httpx.get(
        f"{BASE}/expenses/{ids[0]}",
        headers={"Authorization": "Bearer invalid.token.here"},
    )
    check("invalid token rejected", r.status_code == 401)

    # Ownership isolation
    other_email = f"other{int(time.time())}@example.com"
    httpx.post(f"{BASE}/auth/register", json={"name": "Other", "email": other_email,
                                              "password": password})
    r = httpx.post(f"{BASE}/auth/login", json={"email": other_email, "password": password})
    other_token = r.json()["access_token"]
    r = httpx.get(f"{BASE}/expenses/{ids[0]}", headers={"Authorization": f"Bearer {other_token}"})
    check("user B cannot read user A's expense", r.status_code == 404)

    # --- Budgets & alerts ---
    r = httpx.post(
        f"{BASE}/budgets",
        json={"category": "Food", "amount": 300, "start_date": "2026-09-01",
              "end_date": "2026-09-30", "alert_threshold": 80},
        headers=H,
    )
    check("create category budget (201)", r.status_code == 201)
    budget = r.json()
    util = budget["utilization"]
    check("budget utilization computed", util["amount_spent"] == 250.5
          and util["status"] == "WARNING" and util["utilization_percentage"] >= 80)

    r = httpx.post(
        f"{BASE}/budgets",
        json={"category": "Rent", "amount": 4000, "start_date": "2026-09-01",
              "end_date": "2026-09-30", "alert_threshold": 80},
        headers=H,
    )
    r.json()["utilization"]["status"] == "EXCEEDED"
    exceeded_budget = r.json()
    check("exceeded budget detected", exceeded_budget["utilization"]["status"] == "EXCEEDED")

    r = httpx.get(f"{BASE}/alerts", headers=H)
    alerts = r.json()["items"]
    types = {a["type"] for a in alerts}
    check("warning + exceeded alerts generated", {"warning", "exceeded"} <= types)

    alert_id = alerts[0]["id"]
    r = httpx.patch(f"{BASE}/alerts/{alert_id}/read", headers=H)
    check("mark alert read", r.status_code == 200 and r.json()["is_read"] is True)

    r = httpx.patch(f"{BASE}/alerts/read-all", headers=H)
    check("mark all read", r.status_code == 200)
    r = httpx.get(f"{BASE}/alerts", headers=H)
    check("unread count now 0", r.json()["unread_count"] == 0)

    # --- Analytics ---
    qs = "start_date=2026-09-01&end_date=2026-09-30"
    r = httpx.get(f"{BASE}/analytics/summary?{qs}", headers=H)
    body = r.json()
    check("summary metrics", body["total_expenses"] == 4
          and body["total_amount"] == 6545.5 and body["highest_expense"] == 5000)

    r = httpx.get(f"{BASE}/analytics/categories?{qs}", headers=H)
    rows = r.json()
    check("category aggregation", rows[0]["category"] == "Rent"
          and abs(sum(x["percentage"] for x in rows) - 100) < 1)

    r = httpx.get(f"{BASE}/analytics/trends?granularity=daily&{qs}", headers=H)
    check("trends daily", r.status_code == 200 and len(r.json()) >= 3)

    r = httpx.get(f"{BASE}/analytics/time-series?granularity=daily&{qs}", headers=H)
    body = r.json()
    check("time-series ECharts shape", body["granularity"] == "daily"
          and len(body["points"]) == 16 and "trend_direction" in body)

    r = httpx.get(f"{BASE}/analytics/top-expenses?limit=3&{qs}", headers=H)
    top = r.json()
    check("top-expenses (heap)", [t["amount"] for t in top] == [5000, 1200, 250.5])

    r = httpx.get(f"{BASE}/analytics/insights?{qs}", headers=H)
    msgs = [i["message"] for i in r.json()["insights"]]
    check("insights generated", any("highest expense" in m for m in msgs))

    # --- Cleanup: delete created expense ---
    r = httpx.delete(f"{BASE}/expenses/{ids[3]}", headers=H)
    check("delete expense (204)", r.status_code == 204)

    print(f"\n{ok} passed, {failed} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
