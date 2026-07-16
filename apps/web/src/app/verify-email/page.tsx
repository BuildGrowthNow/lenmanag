"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";

import { verifyEmail } from "@/lib/api/users";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

function VerifyEmailContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");

  const [status, setStatus] = useState<"verifying" | "success" | "error">("verifying");
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!token) {
      setStatus("error");
      setMessage("No verification token provided");
      return;
    }

    verifyEmail(token)
      .then((data) => {
        setStatus("success");
        setMessage(`Email ${data.email} verified successfully!`);
      })
      .catch((error) => {
        setStatus("error");
        setMessage(error instanceof Error ? error.message : "Verification failed");
      });
  }, [token]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-[radial-gradient(circle_at_top,_rgba(255,255,255,0.05),_transparent_26%),linear-gradient(180deg,_#0c1016_0%,_#070a0f_100%)] px-4">
      <Card className="w-full max-w-lg">
        <CardHeader>
          <CardTitle style={{ fontFamily: "var(--font-heading)" }} className="text-2xl">
            Email Verification
          </CardTitle>
          <CardDescription>
            {status === "verifying" && "Verifying your email address..."}
            {status === "success" && "Your email has been verified"}
            {status === "error" && "Verification failed"}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {status === "verifying" && (
            <div className="flex justify-center py-8">
              <div className="h-8 w-8 animate-spin rounded-full border-4 border-muted border-t-text" />
            </div>
          )}

          {status === "success" && (
            <>
              <div className="rounded-2xl border border-success/30 bg-success/10 px-4 py-3 text-sm text-text">
                {message}
              </div>
              <Button className="w-full" onClick={() => router.push("/app")}>
                Go to Dashboard
              </Button>
            </>
          )}

          {status === "error" && (
            <>
              <div className="rounded-2xl border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-text">
                {message}
              </div>
              <div className="text-center">
                <Link href="/login" className="text-sm text-muted hover:text-text hover:underline">
                  Return to login
                </Link>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <VerifyEmailContent />
    </Suspense>
  );
}
