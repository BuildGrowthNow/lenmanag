"use client";

import { useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";

import { resetPassword } from "@/lib/api/users";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

const PASSWORD_REQUIREMENTS = [
  { test: (p: string) => p.length >= 8, label: "At least 8 characters" },
  { test: (p: string) => /[A-Z]/.test(p), label: "One uppercase letter" },
  { test: (p: string) => /[a-z]/.test(p), label: "One lowercase letter" },
  { test: (p: string) => /\d/.test(p), label: "One number" },
  { test: (p: string) => /[!@#$%^&*(),.?":{}|<>_\-+=[\]\\;'/`~]/.test(p), label: "One special character" },
];

function ResetPasswordContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [busy, setBusy] = useState(false);

  const allRequirementsMet = PASSWORD_REQUIREMENTS.every((req) => req.test(password));
  const passwordsMatch = password === confirmPassword && password.length > 0;

  async function handleSubmit() {
    if (!token) {
      setError("No reset token provided");
      return;
    }

    if (!allRequirementsMet) {
      setError("Password does not meet all requirements");
      return;
    }

    if (!passwordsMatch) {
      setError("Passwords do not match");
      return;
    }

    setBusy(true);
    setError(null);
    try {
      await resetPassword(token, password);
      setSuccess(true);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Reset failed");
    } finally {
      setBusy(false);
    }
  }

  if (!token) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[radial-gradient(circle_at_top,_rgba(255,255,255,0.05),_transparent_26%),linear-gradient(180deg,_#0c1016_0%,_#070a0f_100%)] px-4">
        <Card className="w-full max-w-lg">
          <CardHeader>
            <CardTitle style={{ fontFamily: "var(--font-heading)" }} className="text-2xl">
              Invalid link
            </CardTitle>
            <CardDescription>
              This password reset link is invalid or has expired.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="rounded-2xl border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-text">
              No reset token was provided. Please request a new password reset link.
            </div>
            <div className="text-center">
              <Link href="/forgot-password" className="text-sm text-text hover:underline">
                Request new reset link
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (success) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[radial-gradient(circle_at_top,_rgba(255,255,255,0.05),_transparent_26%),linear-gradient(180deg,_#0c1016_0%,_#070a0f_100%)] px-4">
        <Card className="w-full max-w-lg">
          <CardHeader>
            <CardTitle style={{ fontFamily: "var(--font-heading)" }} className="text-2xl">
              Password reset successful
            </CardTitle>
            <CardDescription>
              Your password has been changed. You can now sign in with your new password.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="rounded-2xl border border-success/30 bg-success/10 px-4 py-3 text-sm text-text">
              Your password has been updated successfully.
            </div>
            <Button className="w-full" onClick={() => router.push("/login")}>
              Sign in
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[radial-gradient(circle_at_top,_rgba(255,255,255,0.05),_transparent_26%),linear-gradient(180deg,_#0c1016_0%,_#070a0f_100%)] px-4">
      <Card className="w-full max-w-lg">
        <CardHeader>
          <CardTitle style={{ fontFamily: "var(--font-heading)" }} className="text-2xl">
            Reset your password
          </CardTitle>
          <CardDescription>
            Enter your new password below.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm text-muted" htmlFor="password">
              New Password
            </label>
            <Input
              id="password"
              type="password"
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter new password"
            />
          </div>

          <div className="space-y-1">
            <p className="text-xs text-muted">Password requirements:</p>
            <ul className="space-y-1 text-xs">
              {PASSWORD_REQUIREMENTS.map((req, i) => (
                <li
                  key={i}
                  className={req.test(password) ? "text-success" : "text-muted"}
                >
                  {req.test(password) ? "✓" : "○"} {req.label}
                </li>
              ))}
            </ul>
          </div>

          <div className="space-y-2">
            <label className="text-sm text-muted" htmlFor="confirm-password">
              Confirm Password
            </label>
            <Input
              id="confirm-password"
              type="password"
              autoComplete="new-password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && void handleSubmit()}
              placeholder="Confirm new password"
            />
            {confirmPassword.length > 0 && (
              <p className={`text-xs ${passwordsMatch ? "text-success" : "text-danger"}`}>
                {passwordsMatch ? "✓ Passwords match" : "Passwords do not match"}
              </p>
            )}
          </div>

          {error ? (
            <div className="rounded-2xl border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-text">
              {error}
            </div>
          ) : null}

          <Button
            className="w-full"
            disabled={busy || !allRequirementsMet || !passwordsMatch}
            onClick={() => void handleSubmit()}
          >
            {busy ? "Resetting..." : "Reset password"}
          </Button>

          <div className="text-center text-sm text-muted">
            Remember your password?{" "}
            <Link href="/login" className="text-text hover:underline">
              Sign in
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<div className="flex min-h-screen items-center justify-center">Loading...</div>}>
      <ResetPasswordContent />
    </Suspense>
  );
}
