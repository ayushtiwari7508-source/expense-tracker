"use client";

import { useState, type FormEvent } from "react";
import { PageHeader } from "@/components/PageHeader";
import { Button, Card, CardHeader, Field, Input } from "@/components/ui";
import { authApi } from "@/lib/api";
import { ApiError, useAuth } from "@/lib/auth-context";
import { useToast } from "@/lib/toast-context";

export default function SettingsPage() {
  const { user, refreshUser, logout } = useAuth();
  const toast = useToast();

  // Profile form
  const [name, setName] = useState(user?.name ?? "");
  const [email, setEmail] = useState(user?.email ?? "");
  const [savingProfile, setSavingProfile] = useState(false);
  const [profileError, setProfileError] = useState<string | null>(null);

  // Password form
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [savingPassword, setSavingPassword] = useState(false);
  const [passwordError, setPasswordError] = useState<string | null>(null);

  async function saveProfile(event: FormEvent) {
    event.preventDefault();
    setProfileError(null);
    setSavingProfile(true);
    try {
      await authApi.updateMe({ name: name.trim(), email: email.trim() });
      await refreshUser();
      toast.success("Profile updated.");
    } catch (error) {
      setProfileError(
        error instanceof ApiError && error.status === 409
          ? "That email is already in use."
          : error instanceof Error
            ? error.message
            : "Could not update profile.",
      );
    } finally {
      setSavingProfile(false);
    }
  }

  async function savePassword(event: FormEvent) {
    event.preventDefault();
    setPasswordError(null);
    if (newPassword.length < 8 || !/[A-Z]/.test(newPassword) || !/[a-z]/.test(newPassword) || !/\d/.test(newPassword)) {
      setPasswordError("New password needs 8+ characters with uppercase, lowercase, and a digit.");
      return;
    }
    setSavingPassword(true);
    try {
      await authApi.changePassword({ current_password: currentPassword, new_password: newPassword });
      toast.success("Password changed. Please sign in again.");
      logout();
    } catch (error) {
      setPasswordError(
        error instanceof ApiError && error.status === 401
          ? "Current password is incorrect."
          : error instanceof Error
            ? error.message
            : "Could not change password.",
      );
    } finally {
      setSavingPassword(false);
    }
  }

  return (
    <>
      <PageHeader title="Settings" description="Your account details." />

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader title="Profile" />
          <form onSubmit={saveProfile} className="flex flex-col gap-4 p-4" noValidate>
            {profileError && (
              <p className="rounded border border-error/30 bg-error/5 px-3 py-2 text-sm text-error" role="alert">
                {profileError}
              </p>
            )}
            <Field label="Name" htmlFor="settings-name">
              <Input id="settings-name" required minLength={2} value={name} onChange={(e) => setName(e.target.value)} />
            </Field>
            <Field label="Email" htmlFor="settings-email">
              <Input
                id="settings-email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </Field>
            <div className="flex justify-end">
              <Button type="submit" loading={savingProfile}>
                Save profile
              </Button>
            </div>
          </form>
        </Card>

        <Card>
          <CardHeader title="Change password" />
          <form onSubmit={savePassword} className="flex flex-col gap-4 p-4" noValidate>
            {passwordError && (
              <p className="rounded border border-error/30 bg-error/5 px-3 py-2 text-sm text-error" role="alert">
                {passwordError}
              </p>
            )}
            <Field label="Current password" htmlFor="settings-current">
              <Input
                id="settings-current"
                type="password"
                autoComplete="current-password"
                required
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
              />
            </Field>
            <Field
              label="New password"
              htmlFor="settings-new"
              hint="8+ characters with uppercase, lowercase, and a digit."
            >
              <Input
                id="settings-new"
                type="password"
                autoComplete="new-password"
                required
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
              />
            </Field>
            <div className="flex justify-end">
              <Button type="submit" loading={savingPassword}>
                Change password
              </Button>
            </div>
          </form>
        </Card>
      </div>
    </>
  );
}
