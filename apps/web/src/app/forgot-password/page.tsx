"use client";

import { useState } from "react";
import Link from "next/link";

import { forgotPassword } from "@/lib/api/users";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [busy, setBusy] = useState(false);

  async function handleSubmit() {
    setBusy(true);
    setError(null);
    try {
      await forgotPassword(email);
      setSuccess(true);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Request failed");
    } finally {
      setBusy(false);
    }
  }

  if (success) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[radial-gradient(circle_at_top,_rgba(255,255,255,0.05),_transparent_26%),linear-gradient(180deg,_#0c1016_0%,_#070a0f_100%)] px-4">
        <Card className="w-full max-w-lg">
          <CardHeader>
            <CardTitle style={{ fontFamily: "var(--font-heading)" }} className="text-2xl">
              Check your email
            </CardTitle>
            <CardDescription>
              If an account exists for {email}, we sent a password reset link.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="rounded-2xl border border-success/30 bg-success/10 px-4 py-3 text-sm text-text">
              Please check your inbox and spam folder. The link expires in 24 hours.
            </div>
            <div className="text-center">
              <Link href="/login" className="text-sm text-muted hover:text-text hover:underline">
                Return to login
              </Link>
            </div>
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
            Forgot your password?
          </CardTitle>
          <CardDescription>
            Enter your email address and we&apos;ll send you a link to reset your password.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm text-muted" htmlFor="email">
              Email
            </label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && void handleSubmit()}
              placeholder="you@example.com"
            />
          </div>
          {error ? (
            <div className="rounded-2xl border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-text">
              {error}
            </div>
          ) : null}
          <Button
            className="w-full"
            disabled={busy || !email}
            onClick={() => void handleSubmit()}
          >
            {busy ? "Sending..." : "Send reset link"}
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
