// Typed client for the FastAPI backend.
//
// Authentication uses an HttpOnly cookie: the browser attaches it
// automatically to same-origin API requests (`credentials: "include"`),
// and JavaScript never reads or stores the token.

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(
  method: string,
  path: string,
  options: { body?: unknown; query?: Record<string, string | number | boolean | undefined> } = {},
): Promise<T> {
  const url = new URL(`${API_BASE}${path}`);
  if (options.query) {
    for (const [key, value] of Object.entries(options.query)) {
      if (value !== undefined && value !== "") url.searchParams.set(key, String(value));
    }
  }

  // The auth cookie travels with every request; no Authorization header is
  // constructed in JS and the token is never readable by this code.
  let response: Response;
  try {
    response = await fetch(url.toString(), {
      method,
      credentials: "include",
      headers: options.body !== undefined ? { "Content-Type": "application/json" } : undefined,
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    });
  } catch {
    throw new ApiError(0, "Cannot reach the server. Check your connection and try again.");
  }

  if (response.status === 204) return undefined as T;

  let payload: unknown = null;
  try {
    payload = await response.json();
  } catch {
    // non-JSON error body
  }

  if (!response.ok) {
    const detail =
      payload && typeof payload === "object" && "detail" in payload
        ? String((payload as { detail: unknown }).detail)
        : `Request failed (${response.status})`;
    throw new ApiError(response.status, detail);
  }
  return payload as T;
}

export const api = {
  get: <T>(path: string, query?: Record<string, string | number | boolean | undefined>) =>
    request<T>("GET", path, { query }),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, { body }),
  patch: <T>(path: string, body?: unknown) => request<T>("PATCH", path, { body }),
  delete: <T>(path: string) => request<T>("DELETE", path),
};

// ---------------------------------------------------------------- endpoints

import type {
  Alert,
  AlertList,
  Budget,
  CategoryAnalyticsItem,
  Expense,
  ExpenseList,
  InsightsResponse,
  Summary,
  TimeSeries,
  TopExpenseItem,
  TrendPoint,
  User,
} from "./types";

export const authApi = {
  register: (data: { name: string; email: string; password: string }) =>
    api.post<User>("/auth/register", data),
  /** Login sets the HttpOnly auth cookie and returns the user profile
   *  (the token itself is never in the response body). */
  login: (data: { email: string; password: string }) => api.post<User>("/auth/login", data),
  me: () => api.get<User>("/auth/me"),
  updateMe: (data: { name?: string; email?: string }) => api.patch<User>("/users/me", data),
  changePassword: (data: { current_password: string; new_password: string }) =>
    api.patch<{ detail: string }>("/users/me/password", data),
  /** Logout clears the auth cookie server-side. */
  logout: () => api.post<{ detail: string }>("/auth/logout"),
};

export const expenseApi = {
  list: (query: Record<string, string | number | boolean | undefined>) =>
    api.get<ExpenseList>("/expenses", query),
  get: (id: string) => api.get<Expense>(`/expenses/${id}`),
  create: (data: Omit<Expense, "id" | "user_id" | "created_at" | "updated_at">) =>
    api.post<Expense>("/expenses", data),
  update: (id: string, data: Partial<Omit<Expense, "id" | "user_id" | "created_at" | "updated_at">>) =>
    api.patch<Expense>(`/expenses/${id}`, data),
  remove: (id: string) => api.delete<void>(`/expenses/${id}`),
};

export const budgetApi = {
  list: () => api.get<Budget[]>("/budgets"),
  create: (data: {
    category: string | null;
    amount: number;
    start_date: string;
    end_date: string;
    alert_threshold: number;
  }) => api.post<Budget>("/budgets", data),
  update: (
    id: string,
    data: {
      category?: string | null;
      amount?: number;
      start_date?: string;
      end_date?: string;
      alert_threshold?: number;
    },
  ) => api.patch<Budget>(`/budgets/${id}`, data),
  remove: (id: string) => api.delete<void>(`/budgets/${id}`),
};

export const alertApi = {
  list: (unreadOnly = false) => api.get<AlertList>("/alerts", { unread_only: unreadOnly }),
  markRead: (id: string) => api.patch<Alert>(`/alerts/${id}/read`),
  markAllRead: () => api.patch<{ detail: string }>("/alerts/read-all"),
};

export const analyticsApi = {
  summary: (startDate?: string, endDate?: string) =>
    api.get<Summary>("/analytics/summary", { start_date: startDate, end_date: endDate }),
  categories: (startDate?: string, endDate?: string) =>
    api.get<CategoryAnalyticsItem[]>("/analytics/categories", { start_date: startDate, end_date: endDate }),
  trends: (granularity: string, startDate?: string, endDate?: string) =>
    api.get<TrendPoint[]>("/analytics/trends", { granularity, start_date: startDate, end_date: endDate }),
  timeSeries: (granularity: string, startDate?: string, endDate?: string, maWindow?: number) =>
    api.get<TimeSeries>("/analytics/time-series", {
      granularity,
      start_date: startDate,
      end_date: endDate,
      moving_average_window: maWindow,
    }),
  topExpenses: (limit: number, startDate?: string, endDate?: string) =>
    api.get<TopExpenseItem[]>("/analytics/top-expenses", { limit, start_date: startDate, end_date: endDate }),
  insights: (startDate?: string, endDate?: string) =>
    api.get<InsightsResponse>("/analytics/insights", { start_date: startDate, end_date: endDate }),
};
