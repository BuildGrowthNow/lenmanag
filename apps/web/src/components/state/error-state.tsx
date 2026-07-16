import Link from "next/link";

import { Button } from "@/components/ui/button";

export function ErrorState({ title, description }: { title: string; description: string }) {
  return (
    <div className="rounded-3xl border border-danger/30 bg-danger/10 p-8 text-sm text-text">
      <h2 className="text-lg font-semibold">{title}</h2>
      <p className="mt-2 max-w-2xl leading-6 text-muted">{description}</p>
      <div className="mt-5">
        <Button variant="secondary">
          <Link href="/app">Return to dashboard</Link>
        </Button>
      </div>
    </div>
  );
}
