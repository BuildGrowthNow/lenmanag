"use client";

import { motion } from "framer-motion";
import { useEffect, useState } from "react";

interface GradientMeshProps {
  colors: string[];
  animated?: boolean;
  className?: string;
}

export function GradientMesh({ colors, animated = true, className = "" }: GradientMeshProps) {
  const [gradientPositions, setGradientPositions] = useState(
    colors.map((_, i) => ({
      x: 25 + (i * 50) % 100,
      y: 25 + ((i * 37) % 3) * 25,
    }))
  );

  useEffect(() => {
    if (!animated) return;

    const interval = setInterval(() => {
      setGradientPositions((prev) =>
        prev.map((pos) => ({
          x: (pos.x + Math.random() * 10 - 5 + 100) % 100,
          y: (pos.y + Math.random() * 10 - 5 + 100) % 100,
        }))
      );
    }, 3000);

    return () => clearInterval(interval);
  }, [animated]);

  const gradientStops = colors
    .map((color, i) => {
      const pos = gradientPositions[i];
      return `radial-gradient(circle at ${pos.x}% ${pos.y}%, ${color} 0%, transparent 50%)`;
    })
    .join(", ");

  return (
    <motion.div
      className={`absolute inset-0 opacity-30 blur-3xl ${className}`}
      style={{
        background: gradientStops,
      }}
      animate={animated ? { opacity: [0.3, 0.5, 0.3] } : undefined}
      transition={
        animated
          ? {
              duration: 8,
              repeat: Infinity,
              ease: "easeInOut",
            }
          : undefined
      }
    />
  );
}

interface AnimatedGradientProps {
  colors: [string, string];
  direction?: "to-r" | "to-br" | "to-b" | "to-bl";
  animated?: boolean;
  className?: string;
}

export function AnimatedGradient({
  colors,
  direction = "to-br",
  animated = true,
  className = "",
}: AnimatedGradientProps) {
  return (
    <motion.div
      className={`bg-gradient-${direction} ${className}`}
      style={{
        backgroundImage: `linear-gradient(${direction.replace("to-", "")}, ${colors[0]}, ${colors[1]})`,
      }}
      animate={
        animated
          ? {
              backgroundPosition: ["0% 50%", "100% 50%", "0% 50%"],
            }
          : undefined
      }
      transition={
        animated
          ? {
              duration: 10,
              repeat: Infinity,
              ease: "easeInOut",
            }
          : undefined
      }
    />
  );
}
