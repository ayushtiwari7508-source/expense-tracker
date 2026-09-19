import { APIRequestContext, ConsoleMessage, Page, Response, TestInfo } from "@playwright/test";

/**
 * Base URL of the FastAPI backend. Tests talk to it directly for test-data
 * setup/teardown (never to fake the app – the UI itself is always exercised).
 *
 * Authentication is cookie-based: login/register responses set the HttpOnly
 * auth cookie in the Playwright cookie jar, which is shared with the browser
 * context, so API-seeded sessions authenticate the browser automatically.
 * No test ever handles a raw JWT.
 */
export const API_BASE_URL = process.env.API_BASE_URL ?? "http://localhost:8000";
const API_ROOT = API_BASE_URL.replace(/\/$/, "");

export interface TestUser {
  name: string;
  email: string;
  password: string;
}

const RUN_TAG = process.env.PLAYWRIGHT_TEST_ID ?? "e2e";

/**
 * Unique, collision-safe test email for this worker/run.
 * Uses a non-reserved TLD: the backend's email validation (email-validator)
 * rejects special-use names like `.test` or `example.com`.
 */
export function uniqueEmail(prefix = "user"): string {
  const random = Math.random().toString(36).slice(2, 8);
  return `${RUN_TAG}.${prefix}.${Date.now().toString(36)}.${random}@e2e-tests.dev`;
}

export const TEST_PASSWORD = "Sup3r-Secret-Pw!";

export interface AuthResult {
  user: TestUser;
}

/** Register a brand-new user through the real API and log them in. */
export async function registerUser(
  request: APIRequestContext,
  overrides: Partial<TestUser> = {},
): Promise<AuthResult> {
  const user: TestUser = {
    name: "Playwright Test User",
    email: uniqueEmail(),
    password: TEST_PASSWORD,
    ...overrides,
  };
  const res = await request.post(`${API_ROOT}/api/v1/auth/register`, { data: user });
  if (!res.ok()) {
    throw new Error(`registerUser failed: ${res.status()} ${await res.text()}`);
  }
  // Login sets the HttpOnly auth cookie in the shared cookie jar.
  const login = await request.post(`${API_ROOT}/api/v1/auth/login`, {
    data: { email: user.email, password: user.password },
  });
  if (!login.ok()) {
    throw new Error(`registerUser login failed: ${login.status()} ${await login.text()}`);
  }
  return { user };
}

export interface ExpenseInput {
  amount: number;
  category: string;
  description?: string | null;
  payment_method: string;
  expense_date: string; // YYYY-MM-DD
}

export interface BudgetInput {
  category?: string | null;
  amount: number;
  start_date: string;
  end_date?: string | null;
  alert_threshold: number;
}

/** Create an expense directly (setup only) via the real API (cookie auth). */
export async function createExpenseApi(
  request: APIRequestContext,
  expense: ExpenseInput,
): Promise<void> {
  const res = await request.post(`${API_ROOT}/api/v1/expenses`, { data: expense });
  if (!res.ok()) throw new Error(`createExpenseApi failed: ${res.status()} ${await res.text()}`);
}

/** Create a budget directly (setup only) via the real API (cookie auth). */
export async function createBudgetApi(
  request: APIRequestContext,
  budget: BudgetInput,
): Promise<void> {
  const res = await request.post(`${API_ROOT}/api/v1/budgets`, { data: budget });
  if (!res.ok()) throw new Error(`createBudgetApi failed: ${res.status()} ${await res.text()}`);
}

/** Wipe all expenses/budgets (and cascaded alerts) for the session's user. */
export async function cleanupUser(request: APIRequestContext): Promise<void> {
  for (const path of ["/api/v1/expenses", "/api/v1/budgets"]) {
    const res = await request.get(`${API_ROOT}${path}`);
    if (!res.ok()) continue;
    const body = (await res.json()) as { items?: Array<{ id: string }> };
    for (const item of body.items ?? []) {
      await request.delete(`${API_ROOT}${path}/${item.id}`);
    }
  }
}

export const CATEGORIES = [
  "Food",
  "Travel",
  "Shopping",
  "Education",
  "Entertainment",
  "Bills",
  "Healthcare",
  "Rent",
  "Other",
] as const;
export const PAYMENT_METHODS = [
  "Cash",
  "UPI",
  "Credit Card",
  "Debit Card",
  "Bank Transfer",
  "Other",
] as const;

/* ------------------------------------------------------------------ */
/* Console + network audit                                             */
/* ------------------------------------------------------------------ */

const IGNORED_CONSOLE_PATTERNS: RegExp[] = [
  // Next.js dev-mode noise, documented intentionally – not app errors.
  /Download the React DevTools/,
  /\[Fast Refresh\]/,
  /Fast Refresh had to perform a full reload/,
  /webpack/i,
  /Warning: Extra attributes from the server/,
  /imagesrcset|imageSizes/i,
];

const IGNORED_REQUEST_PATTERNS: RegExp[] = [
  // Dev tooling endpoints, not app API calls.
  /_next\/webpack-hmr/,
  /_next\/static.*\.hot-update/,
  /favicon\.ico/,
  /__nextjs/,
];

/**
 * Attach console + failed-response capture to a page.
 */
export function attachAudits(page: Page) {
  const consoleErrors: string[] = [];
  const pageErrors: string[] = [];
  const failedRequests: Array<{ url: string; status: number | null; failure?: string }> = [];

  const onConsole = (msg: ConsoleMessage) => {
    if (msg.type() !== "error") return;
    // Cookie-auth bootstrap: the app probes /auth/me on every page load; for
    // anonymous visitors that is an expected 401 (browsers always log failed
    // resource loads). The login page itself is handled by app state.
    const loc = msg.location()?.url ?? "";
    if (loc.includes("/auth/me") && msg.text().includes("401")) return;
    if (!IGNORED_CONSOLE_PATTERNS.some((p) => p.test(msg.text()))) {
      consoleErrors.push(msg.text());
    }
  };
  const onPageError = (error: Error) => {
    pageErrors.push(error.message);
  };
  const onResponse = (response: Response) => {
    const url = response.url();
    if (IGNORED_REQUEST_PATTERNS.some((p) => p.test(url))) return;
    if (response.status() >= 500 || response.status() === 0) {
      failedRequests.push({ url, status: response.status() });
    }
  };
  const onRequestFailed = (req: import("@playwright/test").Request) => {
    if (IGNORED_REQUEST_PATTERNS.some((p) => p.test(req.url()))) return;
    const errorText = req.failure()?.errorText ?? "";
    // net::ERR_ABORTED is emitted when a completed request's context is torn
    // down (page close/navigation). It is not an application failure; real
    // network problems surface as ERR_FAILED / ERR_CONNECTION_REFUSED / etc.
    if (errorText.includes("ERR_ABORTED")) return;
    failedRequests.push({ url: req.url(), status: null, failure: errorText });
  };

  page.on("console", onConsole);
  page.on("pageerror", onPageError);
  page.on("response", onResponse);
  page.on("requestfailed", onRequestFailed);

  return {
    consoleErrors,
    pageErrors,
    failedRequests,
    /** Remove entries for URLs a test *intentionally* broke (error-state specs). */
    dismissFailed(predicate: (url: string) => boolean) {
      for (let i = failedRequests.length - 1; i >= 0; i -= 1) {
        if (predicate(failedRequests[i].url)) failedRequests.splice(i, 1);
      }
    },
    /** Drop intentionally-captured console errors matched by predicate. */
    dismissConsole(predicate: (text: string) => boolean) {
      for (let i = consoleErrors.length - 1; i >= 0; i -= 1) {
        if (predicate(consoleErrors[i])) consoleErrors.splice(i, 1);
      }
    },
    detach() {
      page.off("console", onConsole);
      page.off("pageerror", onPageError);
      page.off("response", onResponse);
      page.off("requestfailed", onRequestFailed);
    },
  };
}

export type Audits = ReturnType<typeof attachAudits>;

/** Throws with a readable summary when unexpected browser errors occurred. */
export function assertNoUnexpectedErrors(audits: Audits, testInfo: TestInfo) {
  const problems: string[] = [];
  if (audits.pageErrors.length) {
    problems.push(`Uncaught page errors:\n  ${audits.pageErrors.join("\n  ")}`);
  }
  if (audits.consoleErrors.length) {
    problems.push(`console.error:\n  ${audits.consoleErrors.join("\n  ")}`);
  }
  if (audits.failedRequests.length) {
    problems.push(
      `Failed network requests:\n  ${audits.failedRequests
        .map((f) => `${f.status ?? "ERR"} ${f.url} ${f.failure ?? ""}`)
        .join("\n  ")}`,
    );
  }
  if (problems.length) {
    testInfo.annotations.push({ type: "audit", description: problems.join("\n\n") });
    throw new Error(`Unexpected browser errors in "${testInfo.title}":\n${problems.join("\n\n")}`);
  }
}
