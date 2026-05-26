import * as React from "react";

import { cn } from "@/lib/utils";

export function Badge({ className, children }: React.PropsWithChildren<{ className?: string }>) {
  return <span className={cn("inline-flex items-center rounded-full border border-line bg-white/4 px-2.5 py-1 text-xs font-medium text-text", className)}>{children}</span>;
}

