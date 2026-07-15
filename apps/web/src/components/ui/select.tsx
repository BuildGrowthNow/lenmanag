import * as React from "react";

import { cn } from "@/lib/utils";

export function Select({ className, children, ...props }: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={cn(
        "h-11 w-full rounded-xl border border-line bg-panel px-3 text-sm text-text focus:outline-none focus:ring-2 focus:ring-white/20",
        className
      )}
      {...props}
    >
      {children}
    </select>
  );
}

export function SelectTrigger({ className, children, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      className={cn(
        "h-11 w-full rounded-xl border border-line bg-panel px-3 text-sm text-text focus:outline-none focus:ring-2 focus:ring-white/20",
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
}

export function SelectContent({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "rounded-xl border border-line bg-panel p-2",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

export function SelectItem({ className, children, ...props }: React.OptionHTMLAttributes<HTMLOptionElement>) {
  return (
    <option
      className={cn("text-sm text-text", className)}
      {...props}
    >
      {children}
    </option>
  );
}

export function SelectValue({ placeholder }: { placeholder?: string }) {
  return <span className="text-sm text-muted">{placeholder}</span>;
}
