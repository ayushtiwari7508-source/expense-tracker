"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { Wallet } from "lucide-react";
import { ApiError, useAuth } from "@/lib/auth-context";
import { Button, Field, Input } from "@/components/ui";

function passwordProblem(password: string): string | null {
  if (password.length < 8) return "At least 8 characters.";
  if (!/[A-Z]/.test(password)) return "Add an uppercase letter.";
  if (!/[a-z]/.test(password)) return "Add a lowercase letter.";
  if (!/\d/.test(password)) return "Add a digit.";
  return null;
}

export default function RegisterPage() {
  const { register } = useAuth();
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setFormError(null);

    const errors: Record<string, string> = {};
    if (name.trim().length < 2) errors.name = "Enter your name.";
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email.trim())) errors.email = "Enter a valid email.";
    const pw = passwordProblem(password);
    if (pw) errors.password = pw;
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) return;

    setSubmitting(true);
    try {
      await register(name.trim(), email.trim(), password);
      router.push("/dashboard");
    } catch (err) {
      setFormError(
        err instanceof ApiError && err.status === 409
          ? "That email is already registered. Try signing in."
          : err instanceof Error
            ? err.message
            : "Could not create the account.",
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

      <h1 className="text-xl font-semibold tracking-tight text-foreground">Create an account</h1>
      <p className="mt-0.5 text-sm text-muted">Start tracking expenses in a minute.</p>

      <form onSubmit={onSubmit} className="mt-6 flex flex-col gap-4" noValidate>
        {formError && (
          <p className="rounded border border-error/30 bg-error/5 px-3 py-2 text-sm text-error" role="alert">
            {formError}
          </p>
        )}
        <Field label="Name" htmlFor="name" error={fieldErrors.name}>
          <Input
            id="name"
            autoComplete="name"
            required
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Ayush"
          />
        </Field>
        <Field label="Email" htmlFor="email" error={fieldErrors.email}>
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
        <Field
          label="Password"
          htmlFor="password"
          error={fieldErrors.password}
          hint="At least 8 characters with uppercase, lowercase, and a digit."
        >
          <Input
            id="password"
            type="password"
            autoComplete="new-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </Field>
        <Button type="submit" loading={submitting}>
          Create account
        </Button>
      </form>

      <p className="mt-6 text-sm text-muted">
        Already registered?{" "}
        <Link href="/login" className="font-medium text-primary hover:underline">
          Sign in
        </Link>
      </p>
    </div>
  );
}
