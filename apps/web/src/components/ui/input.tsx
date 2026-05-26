import * as React from "react";

import { cn } from "@/lib/utils";

export function Input({ className, ...props }: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "h-11 w-full rounded-xl border border-line bg-panel px-3 text-sm text-text placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-white/20",
        className
      )}
      {...props}
    />
  );
}

