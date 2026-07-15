"use client";

import { motion, useInView, useMotionValue, useSpring } from "framer-motion";
import { useEffect, useRef } from "react";
import { cn } from "@/lib/utils";

interface CountUpStatsProps {
  value: number;
  duration?: number;
  suffix?: string;
  prefix?: string;
  label?: string;
  className?: string;
}

export function CountUpStats({
  value,
  duration = 2,
  suffix = "",
  prefix = "",
  label,
  className,
}: CountUpStatsProps) {
  const ref = useRef(null);
  const motionValue = useMotionValue(0);
  const springValue = useSpring(motionValue, {
    damping: 50,
    stiffness: 100,
  });
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  useEffect(() => {
    if (isInView) {
      motionValue.set(value);
    }
  }, [motionValue, isInView, value]);

  useEffect(() => {
    const unsubscribe = springValue.on("change", (latest) => {
      if (ref.current) {
        const displayValue = Math.round(latest);
        (ref.current as HTMLSpanElement).textContent = `${prefix}${displayValue.toLocaleString()}${suffix}`;
      }
    });

    return () => unsubscribe();
  }, [springValue, prefix, suffix]);

  return (
    <div className={cn("flex flex-col items-center gap-2", className)}>
      <motion.span
        ref={ref}
        className="text-4xl font-bold text-text md:text-5xl lg:text-6xl"
        initial={{ opacity: 0, scale: 0.8 }}
        animate={isInView ? { opacity: 1, scale: 1 } : { opacity: 0, scale: 0.8 }}
        transition={{ duration: 0.5 }}
      >
        {prefix}0{suffix}
      </motion.span>
      {label && (
        <motion.p
          className="text-sm text-muted md:text-base"
          initial={{ opacity: 0 }}
          animate={isInView ? { opacity: 1 } : { opacity: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
        >
          {label}
        </motion.p>
      )}
    </div>
  );
}

interface StatsGridProps {
  stats: Array<{
    value: number;
    label: string;
    suffix?: string;
    prefix?: string;
  }>;
  className?: string;
}

export function StatsGrid({ stats, className }: StatsGridProps) {
  return (
    <div
      className={cn(
        "grid grid-cols-2 gap-8 md:grid-cols-4 lg:gap-12",
        className
      )}
    >
      {stats.map((stat, index) => (
        <CountUpStats
          key={index}
          value={stat.value}
          label={stat.label}
          suffix={stat.suffix}
          prefix={stat.prefix}
        />
      ))}
    </div>
  );
}
