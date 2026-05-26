import Link from "next/link";

import { Button } from "@/components/ui/button";

export function UnauthorizedState() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-[radial-gradient(circle_at_top,_rgba(255,255,255,0.05),_transparent_26%),linear-gradient(180deg,_#0c1016_0%,_#070a0f_100%)] px-4">
      <div className="w-full max-w-md rounded-3xl border border-line bg-panel p-8 shadow-glow">
        <div className="text-xs uppercase tracking-[0.3em] text-muted">Access denied</div>
        <h1 style={{ fontFamily: "var(--font-heading)" }} className="mt-3 text-3xl font-semibold text-text">
          Admin allowlist required
        </h1>
        <p className="mt-3 text-sm leading-6 text-muted">
          This control plane is internal only. The email used for login must be on the approved allowlist before the session can be created.
        </p>
        <div className="mt-6 flex gap-3">
          <Button asChild>
            <Link href="/login">Try another email</Link>
          </Button>
          <Button variant="secondary" asChild>
            <Link href="/">Home</Link>
          </Button>
        </div>
      </div>
    </div>
  );
}
