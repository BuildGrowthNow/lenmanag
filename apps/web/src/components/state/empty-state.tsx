import { ReactNode } from "react";

import { Button } from "@/components/ui/button";

export function EmptyState({
  title,
  description,
  action
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="rounded-3xl border border-dashed border-line bg-panel/70 p-8">
      <div className="max-w-xl space-y-3">
        <h2 className="text-lg font-semibold text-text">{title}</h2>
        <p className="text-sm leading-6 text-muted">{description}</p>
      </div>
      {action ? <div className="mt-5">{action}</div> : null}
    </div>
  );
}

