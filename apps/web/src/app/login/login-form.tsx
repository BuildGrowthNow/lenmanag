"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { login } from "@/lib/api/auth";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

export function LoginForm() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  return (
    <div className="flex min-h-screen items-center justify-center bg-[radial-gradient(circle_at_top,_rgba(255,255,255,0.05),_transparent_26%),linear-gradient(180deg,_#0c1016_0%,_#070a0f_100%)] px-4">
      <Card className="w-full max-w-lg">
        <CardHeader>
          <CardTitle style={{ fontFamily: "var(--font-heading)" }} className="text-2xl">
            LenQuant admin access
          </CardTitle>
          <CardDescription>
            Sign in with an approved operator email. This shell is internal only and protected by allowlist validation.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm text-muted" htmlFor="email">
              Email
            </label>
            <Input id="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="operator@example.com" />
          </div>
          <div className="space-y-2">
            <label className="text-sm text-muted" htmlFor="name">
              Display name
            </label>
            <Input id="name" value={name} onChange={(event) => setName(event.target.value)} placeholder="Operator" />
          </div>
          {error ? <div className="rounded-2xl border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-text">{error}</div> : null}
          <Button
            className="w-full"
            disabled={busy || !email}
            onClick={async () => {
              setBusy(true);
              setError(null);
              try {
                const result = await login(email, name || undefined);
                if ((result as { authenticated?: boolean }).authenticated) {
                  router.push("/nsa");
                  router.refresh();
                } else {
                  setError((result as { message?: string }).message || "Access denied.");
                }
              } catch (cause) {
                setError(cause instanceof Error ? cause.message : "Unable to reach auth service.");
              } finally {
                setBusy(false);
              }
            }}
          >
            {busy ? "Checking allowlist..." : "Enter shell"}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
