"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

import { signup } from "@/lib/api/users";
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

export default function SignupPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [signupCode, setSignupCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const allRequirementsMet = PASSWORD_REQUIREMENTS.every((req) => req.test(password));

  async function handleSubmit() {
    setBusy(true);
    setError(null);
    try {
      await signup({ email, password, signup_code: signupCode });
      router.push("/app");
      router.refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Signup failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[radial-gradient(circle_at_top,_rgba(255,255,255,0.05),_transparent_26%),linear-gradient(180deg,_#0c1016_0%,_#070a0f_100%)] px-4">
      <Card className="w-full max-w-lg">
        <CardHeader>
          <CardTitle style={{ fontFamily: "var(--font-heading)" }} className="text-2xl">
            Create your account
          </CardTitle>
          <CardDescription>
            Sign up with a valid signup code to get started.
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
          <div className="space-y-2">
            <label className="text-sm text-muted" htmlFor="password">
              Password
            </label>
            <Input
              id="password"
              type="password"
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
            />
            {password.length > 0 && (
              <div className="space-y-1">
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
            )}
          </div>
          <div className="space-y-2">
            <label className="text-sm text-muted" htmlFor="signup-code">
              Signup Code
            </label>
            <Input
              id="signup-code"
              type="text"
              autoComplete="off"
              value={signupCode}
              onChange={(e) => setSignupCode(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && void handleSubmit()}
              placeholder="Enter your signup code"
            />
          </div>
          {error ? (
            <div className="rounded-2xl border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-text">
              {error}
            </div>
          ) : null}
          <Button
            className="w-full"
            disabled={busy || !email || !allRequirementsMet || !signupCode}
            onClick={() => void handleSubmit()}
          >
            {busy ? "Creating account…" : "Sign up"}
          </Button>
          <div className="text-center text-sm text-muted">
            Already have an account?{" "}
            <Link href="/login" className="text-text hover:underline">
              Sign in
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
