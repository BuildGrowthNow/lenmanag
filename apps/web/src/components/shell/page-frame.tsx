import { ReactNode } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

type PageFrameProps = {
  title: string;
  description: string;
  eyebrow?: string;
  children: ReactNode;
};

export function PageFrame({ title, description, eyebrow, children }: PageFrameProps) {
  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-3 border-b border-line pb-6">
        {eyebrow ? <Badge className="w-fit">{eyebrow}</Badge> : null}
        <div className="max-w-3xl">
          <h1 style={{ fontFamily: "var(--font-heading)" }} className="text-3xl font-semibold tracking-tight text-text">
            {title}
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">{description}</p>
        </div>
      </header>
      {children}
    </div>
  );
}

export function PlaceholderPanel({
  title,
  description,
  action
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <Card className="border-dashed bg-panel/70">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent className="flex items-center justify-between gap-4">
        <div className="text-sm text-muted">Waiting on backend data or a later-phase workflow.</div>
        {action}
      </CardContent>
    </Card>
  );
}
