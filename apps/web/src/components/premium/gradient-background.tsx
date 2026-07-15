"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface GradientBackgroundProps {
  colors?: {
    primary: string;
    secondary: string;
    accent?: string;
  };
  className?: string;
  animated?: boolean;
}

export function GradientBackground({
  colors = {
    primary: "#6366f1",
    secondary: "#8b5cf6",
    accent: "#ec4899",
  },
  className,
  animated = true,
}: GradientBackgroundProps) {
  const gradientStyle = {
    background: `
      radial-gradient(circle at 20% 30%, ${colors.primary}33 0%, transparent 50%),
      radial-gradient(circle at 80% 70%, ${colors.secondary}33 0%, transparent 50%)
      ${colors.accent ? `, radial-gradient(circle at 50% 50%, ${colors.accent}22 0%, transparent 60%)` : ""}
    `,
  };

  if (!animated) {
    return (
      <div
        className={cn("absolute inset-0 -z-10 overflow-hidden", className)}
        style={gradientStyle}
      />
    );
  }

  return (
    <div className={cn("absolute inset-0 -z-10 overflow-hidden", className)}>
      <motion.div
        className="absolute inset-0"
        style={gradientStyle}
        animate={{
          scale: [1, 1.1, 1],
          rotate: [0, 5, 0],
        }}
        transition={{
          duration: 20,
          repeat: Infinity,
          ease: "linear",
        }}
      />
    </div>
  );
}
