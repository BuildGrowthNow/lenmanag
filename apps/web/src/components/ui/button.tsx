import * as React from "react";
import { Slot } from "@radix-ui/react-slot";

import { cn } from "@/lib/utils";

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "default" | "secondary" | "ghost" | "danger";
  asChild?: boolean;
};

export function Button({ className, variant = "default", asChild = false, ...props }: ButtonProps) {
  const variants: Record<NonNullable<ButtonProps["variant"]>, string> = {
    default: "bg-accent text-accentText hover:opacity-95 shadow-glow",
    secondary: "bg-panel-2 text-text border border-line hover:bg-white/6",
    ghost: "bg-transparent text-text hover:bg-white/5",
    danger: "bg-danger text-white hover:opacity-95"
  };
  const Comp = asChild ? Slot : "button";
  return (
    <Comp
      className={cn(
        "inline-flex items-center justify-center rounded-xl px-4 py-2 text-sm font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/30 disabled:pointer-events-none disabled:opacity-50",
        variants[variant],
        className
      )}
      {...props}
    />
  );
}
