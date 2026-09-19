"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { Wallet } from "lucide-react";
import { ApiError, useAuth } from "@/lib/auth-context";
import { Button, Field, Input } from "@/components/ui";

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email.trim(), password);
      router.push("/dashboard");
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 401
          ? "Incorrect email or password."
          : err instanceof Error
            ? err.message
            : "Could not sign in.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-screen w-full max-w-sm flex-col justify-center px-4">
      <div className="mb-6 flex items-center gap-2">
        <Wallet className="h-5 w-5 text-primary" aria-hidden />
        <span className="text-sm font-semibold tracking-tight text-foreground">
          Expense Tracker
        </span>
      </div>

      <h1 className="text-xl font-semibold tracking-tight text-foreground">Sign in</h1>
      <p className="mt-0.5 text-sm text-muted">Use your registered email and password.</p>

      <form onSubmit={onSubmit} className="mt-6 flex flex-col gap-4" noValidate>
        {error && (
          <p className="rounded border border-error/30 bg-error/5 px-3 py-2 text-sm text-error" role="alert">
            {error}
          </p>
        )}
        <Field label="Email" htmlFor="email">
          <Input
            id="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="you@example.com"
          />
        </Field>
        <Field label="Password" htmlFor="password">
          <Input
            id="password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </Field>
        <Button type="submit" loading={submitting}>
          Sign in
        </Button>
      </form>

      <p className="mt-6 text-sm text-muted">
        No account yet?{" "}
        <Link href="/register" className="font-medium text-primary hover:underline">
          Create one
        </Link>
      </p>
    </div>
  );
}
