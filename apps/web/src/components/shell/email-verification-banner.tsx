"use client";

import { useState } from "react";

import { resendVerification, UserResponse } from "@/lib/api/users";
import { Button } from "@/components/ui/button";

interface EmailVerificationBannerProps {
  user: UserResponse | null;
}

export function EmailVerificationBanner({ user }: EmailVerificationBannerProps) {
  const [resending, setResending] = useState(false);
  const [resent, setResent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!user || user.is_verified) {
    return null;
  }

  async function handleResend() {
    if (!user) return;

    setResending(true);
    setError(null);
    try {
      await resendVerification(user.email);
      setResent(true);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Failed to resend");
    } finally {
      setResending(false);
    }
  }

  return (
    <div className="border-b border-warning/30 bg-warning/10 px-4 py-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-text">
          <span className="font-medium">Please verify your email address.</span>{" "}
          Check your inbox for a verification link.
        </p>
        <div className="flex items-center gap-2">
          {error && (
            <span className="text-xs text-danger">{error}</span>
          )}
          {resent ? (
            <span className="text-xs text-success">Verification email sent!</span>
          ) : (
            <Button
              variant="ghost"
              size="sm"
              disabled={resending}
              onClick={() => void handleResend()}
            >
              {resending ? "Sending..." : "Resend email"}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
