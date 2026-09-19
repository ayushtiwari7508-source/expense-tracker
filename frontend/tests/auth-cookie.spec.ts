import { expect } from "@playwright/test";
import { uniqueEmail, TEST_PASSWORD } from "./support/helpers";
import { test } from "./support/fixtures";

const API_BASE = process.env.API_BASE_URL ?? "http://localhost:8000";

/** Register + login through the real UI and land on the dashboard. */
async function loginViaUi(page: import("@playwright/test").Page, email: string) {
  await page.goto("/register");
  await page.getByLabel("Name").fill("Cookie Checker");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(TEST_PASSWORD);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/dashboard/);
}

test.describe("Cookie session security", () => {
  test("JWT lives only in an HttpOnly cookie, never in JS storage", async ({ page }) => {
    await loginViaUi(page, uniqueEmail("cookie"));

    // No JWT-shaped value anywhere in web storage.
    const storage = await page.evaluate(() => ({
      local: Object.fromEntries(Object.entries(window.localStorage)),
      session: Object.fromEntries(Object.entries(window.sessionStorage)),
      cookie: document.cookie,
    }));
    const dump = JSON.stringify(storage);
    expect(dump).not.toContain("eyJ"); // JWT payload/signature prefix
    expect(dump).not.toContain("access_token="); // not JS-readable either
  });

  test("login sets HttpOnly cookie and the body never contains the token", async ({ page }) => {
    const email = uniqueEmail("net");
    await page.goto("/register");
    await page.getByLabel("Name").fill("Cookie Checker");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password", { exact: true }).fill(TEST_PASSWORD);

    const [loginResponse] = await Promise.all([
      page.waitForResponse((res) => res.url().includes("/api/v1/auth/login") && res.status() === 200),
      page.getByRole("button", { name: "Create account" }).click(),
    ]);

    // The token must not be in the response body.
    const body = await loginResponse.text();
    expect(body).not.toContain("access_token");
    expect(body).not.toContain("eyJ");

    // ...and must be set as an HttpOnly cookie.
    const setCookie = (await loginResponse.allHeaders())["set-cookie"] ?? "";
    expect(setCookie).toContain("access_token=");
    expect(setCookie.toLowerCase()).toContain("httponly");
    expect(setCookie.toLowerCase()).toContain("samesite=lax");
    expect(setCookie.toLowerCase()).toContain("path=/");
  });

  test("authenticated requests send the cookie, never an Authorization header", async ({
    page,
  }) => {
    await loginViaUi(page, uniqueEmail("hdr"));

    const authHeaders: string[] = [];
    const apiStatuses: number[] = [];
    page.on("request", (req) => {
      // Skip CORS preflights (no cookies on OPTIONS by spec) and the /auth
      // endpoints themselves: login/register necessarily run *before* any
      // cookie exists, and /me is the boot probe.
      if (
        req.method() !== "OPTIONS" &&
        req.url().includes("/api/v1/") &&
        !req.url().includes("/auth/")
      ) {
        authHeaders.push(req.headers()["authorization"] ?? "");
      }
    });
    page.on("response", (res) => {
      if (res.url().includes("/api/v1/") && !res.url().includes("/auth/")) {
        apiStatuses.push(res.status());
      }
    });

    await page.goto("/expenses");
    await expect(page.getByRole("table").or(page.getByText("No expenses yet"))).toBeVisible();
    await page.goto("/analytics");
    await expect(page.getByRole("heading", { name: "Analytics" })).toBeVisible();

    // Every data request succeeded — proof the cookie authenticated them
    // (browser-added Cookie headers are not visible in request.headers()).
    expect(apiStatuses.length).toBeGreaterThan(0);
    expect(apiStatuses.every((s) => s < 400), `statuses: ${apiStatuses}`).toBeTruthy();

    // No Authorization header was ever constructed by the frontend.
    expect(authHeaders.length).toBeGreaterThan(0);
    expect(
      authHeaders.every((h) => h === ""),
      `Authorization headers seen: ${JSON.stringify(authHeaders)}`,
    ).toBeTruthy();

    // The session cookie exists in the jar and is HttpOnly (JS-invisible).
    const cookie = (await page.context().cookies()).find((c) => c.name === "access_token");
    expect(cookie, "auth cookie present").toBeTruthy();
    expect(cookie!.httpOnly).toBeTruthy();
  });

  test("session survives a page refresh", async ({ page }) => {
    const email = uniqueEmail("refresh");
    await loginViaUi(page, email);

    await page.reload();
    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();

    // And the session is real: /me returns the user through the cookie.
    const me = await page.request.get(`${API_BASE}/api/v1/auth/me`);
    expect(me.status()).toBe(200);
    expect((await me.json()).email).toBe(email);
  });

  test("an invalid cookie is rejected and the app falls back to login", async ({ page }) => {
    await loginViaUi(page, uniqueEmail("bad"));

    // Corrupt the session server-side perception: swap in a tampered cookie.
    await page.context().clearCookies();
    await page.context().addCookies([
      {
        name: "access_token",
        value: "tampered.invalid.token",
        domain: "localhost",
        path: "/",
        httpOnly: true,
      },
    ]);

    await page.goto("/dashboard");
    await expect(page).toHaveURL(/\/login/, { timeout: 15_000 });
  });

  test("logout clears the session server-side", async ({ page }) => {
    await loginViaUi(page, uniqueEmail("out"));

    await page.getByRole("button", { name: "Sign out" }).click();
    await expect(page).toHaveURL(/\/login/);

    // The cookie is gone; the API must reject further calls.
    const me = await page.request.get(`${API_BASE}/api/v1/auth/me`);
    expect(me.status()).toBe(401);
  });
});
