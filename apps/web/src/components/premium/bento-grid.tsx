"use client";

import { motion } from "framer-motion";
import { type ReactNode } from "react";
import { cn } from "@/lib/utils";

interface BentoGridProps {
  children: ReactNode;
  className?: string;
}

interface BentoCardProps {
  children: ReactNode;
  className?: string;
  span?: "1" | "2" | "full";
  hover?: boolean;
}

export function BentoGrid({ children, className }: BentoGridProps) {
  return (
    <div
      className={cn(
        "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 w-full",
        className
      )}
    >
      {children}
    </div>
  );
}

export function BentoCard({
  children,
  className,
  span = "1",
  hover = true,
}: BentoCardProps) {
  const spanClasses = {
    "1": "",
    "2": "md:col-span-2",
    full: "col-span-full",
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-50px" }}
      transition={{ duration: 0.5 }}
      whileHover={hover ? { y: -4, scale: 1.02 } : undefined}
      className={cn(
        "relative overflow-hidden rounded-2xl border border-line bg-panel p-6",
        "transition-shadow duration-300",
        hover && "hover:shadow-glow",
        spanClasses[span],
        className
      )}
    >
      {children}
    </motion.div>
  );
}
