"use client";

// Auth context: holds the current user, exposes login/register/logout.
//
// The JWT lives in an HttpOnly cookie set by the backend; this code never
// sees or stores the token. Session state is restored by calling /auth/me
// (the browser attaches the cookie automatically), which also means
// authentication survives page refreshes.

import { useRouter } from "next/navigation";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { ApiError, authApi } from "./api";
import type { User } from "./types";

interface AuthState {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  const logout = useCallback(async () => {
    try {
      // Server clears the HttpOnly cookie. Best-effort: always drop local
      // session state, even if the request fails.
      await authApi.logout();
    } catch {
      // ignore — the local session is cleared regardless
    }
    setUser(null);
    router.push("/login");
  }, [router]);

  // One global 401 handler: an expired/invalid session signs the user out.
  // Scoped to API requests and excluding the auth endpoints themselves so a
  // failed /auth/me bootstrap or wrong-password login cannot loop redirects.
  useEffect(() => {
    const original = window.fetch;
    window.fetch = async (...args) => {
      const response = await original(...args);
      const url =
        typeof args[0] === "string" || args[0] instanceof URL
          ? String(args[0])
          : (args[0] instanceof Request ? args[0].url : "");
      const isApiCall = url.includes("/api/");
      const isAuthEndpoint = url.includes("/auth/login") || url.includes("/auth/me");
      if (response.status === 401 && isApiCall && !isAuthEndpoint) {
        setUser(null);
        router.push("/login");
      }
      return response;
    };
    return () => {
      window.fetch = original;
    };
  }, [router]);

  // Bootstrap: ask the backend who we are; the cookie decides the answer.
  useEffect(() => {
    let cancelled = false;
    async function bootstrap() {
      try {
        const me = await authApi.me();
        if (!cancelled) setUser(me);
      } catch {
        // 401 or network failure: not signed in.
        if (!cancelled) setUser(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    bootstrap();
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    // The response sets the HttpOnly cookie and returns the profile; the
    // session itself is proven on the next request via the cookie.
    const user = await authApi.login({ email, password });
    setUser(user);
  }, []);

  const register = useCallback(
    async (name: string, email: string, password: string) => {
      await authApi.register({ name, email, password });
      await login(email, password);
    },
    [login],
  );

  const refreshUser = useCallback(async () => {
    const me = await authApi.me();
    setUser(me);
  }, []);

  const value = useMemo(
    () => ({ user, loading, login, register, logout, refreshUser }),
    [user, loading, login, register, logout, refreshUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
}

export { ApiError };
