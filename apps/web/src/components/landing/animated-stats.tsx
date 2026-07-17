"use client";

import { useEffect, useState, useRef } from "react";
import { motion, useInView } from "framer-motion";
import { Clock, Users, Star, TrendingUp } from "lucide-react";
import { useSupportsHover } from "@/hooks/use-supports-hover";

interface StatProps {
  icon: React.ElementType;
  value: number;
  suffix: string;
  label: string;
  delay?: number;
}

function AnimatedStat({ icon: Icon, value, suffix, label, delay = 0 }: StatProps) {
  const [count, setCount] = useState(0);
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true });
  const supportsHover = useSupportsHover();

  useEffect(() => {
    if (!isInView) return;

    const duration = 2000; // 2 seconds
    const steps = 20; // Reduced from 60 for better performance
    const increment = value / steps;
    const stepDuration = duration / steps;

    let current = 0;
    const timer = setInterval(() => {
      current += increment;
      if (current >= value) {
        setCount(value);
        clearInterval(timer);
      } else {
        setCount(Math.floor(current));
      }
    }, stepDuration);

    return () => clearInterval(timer);
  }, [isInView, value]);

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 40 }}
      animate={isInView ? { opacity: 1, y: 0 } : {}}
      transition={{ delay, duration: 0.8 }}
      {...(supportsHover && { whileHover: { scale: 1.05 } })}
      className="text-center p-4 md:p-6 rounded-2xl bg-white/5 backdrop-blur-sm border border-white/10 hover:border-yellow-500/50 transition-all group"
    >
      <div className="mb-2 md:mb-3 flex justify-center">
        <div className="w-10 md:w-12 h-10 md:h-12 rounded-xl bg-gradient-to-br from-yellow-500 to-yellow-600 flex items-center justify-center group-hover:scale-110 transition-transform shadow-lg shadow-yellow-500/30">
          <Icon className="w-5 md:w-6 h-5 md:h-6 text-white" />
        </div>
      </div>
      <div className="text-2xl md:text-4xl font-bold text-white mb-1 tabular-nums">
        {count}
        {suffix}
      </div>
      <div className="text-xs md:text-sm text-slate-400">{label}</div>
    </motion.div>
  );
}

export function AnimatedStats() {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-8 max-w-4xl mx-auto">
      <AnimatedStat icon={Clock} value={3} suffix=" Days" label="Delivery Time" delay={0} />
      <AnimatedStat icon={Users} value={500} suffix="+" label="Happy Clients" delay={0.1} />
      <AnimatedStat icon={Star} value={5} suffix=".0" label="Average Rating" delay={0.2} />
      <AnimatedStat icon={TrendingUp} value={98} suffix="%" label="Satisfaction" delay={0.3} />
    </div>
  );
}
