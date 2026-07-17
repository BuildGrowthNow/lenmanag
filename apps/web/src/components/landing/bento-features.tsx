"use client";

import { motion } from "framer-motion";
import {
  Zap,
  Palette,
  Code,
  Rocket,
  Globe,
  Users,
  LineChart,
  Shield,
} from "lucide-react";
import { useSupportsHover } from "@/hooks/use-supports-hover";

const FEATURES = [
  {
    icon: Zap,
    title: "Lightning Fast",
    description: "3-day delivery guaranteed. No delays, no excuses.",
    color: "from-yellow-500 to-orange-500",
    size: "large",
  },
  {
    icon: Palette,
    title: "Custom Design",
    description: "Unique, brand-matched aesthetics",
    color: "from-purple-500 to-pink-500",
    size: "small",
  },
  {
    icon: Code,
    title: "Premium Tech",
    description: "Built with cutting-edge frameworks",
    color: "from-blue-500 to-cyan-500",
    size: "small",
  },
  {
    icon: Rocket,
    title: "Launch Ready",
    description: "Hosting, SSL, and optimization included. Go live instantly.",
    color: "from-green-500 to-emerald-500",
    size: "large",
  },
  {
    icon: Globe,
    title: "SEO Optimized",
    description: "Rank higher in search results",
    color: "from-pink-500 to-rose-500",
    size: "small",
  },
  {
    icon: LineChart,
    title: "Analytics",
    description: "Track performance from day one",
    color: "from-indigo-500 to-purple-500",
    size: "small",
  },
  {
    icon: Shield,
    title: "Secure & Fast",
    description: "Enterprise-grade security with blazing performance built in.",
    color: "from-slate-500 to-gray-500",
    size: "large",
  },
  {
    icon: Users,
    title: "Direct Support",
    description: "Real humans, real help",
    color: "from-orange-500 to-red-500",
    size: "small",
  },
];

export function BentoFeatures() {
  const supportsHover = useSupportsHover();

  return (
    <section className="relative px-6 py-24 bg-slate-900/50">
      <div className="max-w-7xl mx-auto">
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          transition={{ duration: 0.8 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <h2 className="text-5xl font-bold mb-4">
            Everything You <span className="text-yellow-500">Need</span>
          </h2>
          <p className="text-xl text-slate-400">
            Powerful features wrapped in a beautiful package
          </p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 auto-rows-fr">
          {FEATURES.map((feature, i) => {
            const isLarge = feature.size === "large";
            const colSpan = isLarge ? "md:col-span-2" : "md:col-span-1";
            const rowSpan = isLarge ? "md:row-span-2" : "md:row-span-1";

            return (
              <motion.div
                key={i}
                initial={{ opacity: 0, scale: 0.9 }}
                whileInView={{ opacity: 1, scale: 1 }}
                transition={{ delay: i * 0.05, duration: 0.5 }}
                viewport={{ once: true }}
                {...(supportsHover && {
                  whileHover: {
                    scale: 1.02,
                    rotateY: 5,
                    rotateX: 5,
                  },
                })}
                className={`${colSpan} ${rowSpan} group`}
                style={{ perspective: 1000 }}
              >
                <div
                  className={`h-full p-8 rounded-3xl bg-white/5 backdrop-blur-sm border border-white/10 hover:border-white/20 transition-all relative overflow-hidden ${
                    isLarge ? "min-h-[300px]" : "min-h-[200px]"
                  }`}
                >
                  {/* Gradient Background */}
                  <div
                    className={`absolute inset-0 bg-gradient-to-br ${feature.color} opacity-0 group-hover:opacity-10 transition-opacity duration-500`}
                  />

                  {/* Content */}
                  <div className="relative z-10 h-full flex flex-col">
                    <div
                      className={`w-16 h-16 rounded-2xl bg-gradient-to-br ${feature.color} flex items-center justify-center mb-6 shadow-lg group-hover:scale-110 transition-transform`}
                    >
                      <feature.icon className="w-8 h-8 text-white" />
                    </div>

                    <h3
                      className={`font-bold text-white mb-3 ${
                        isLarge ? "text-3xl" : "text-xl"
                      }`}
                    >
                      {feature.title}
                    </h3>

                    <p
                      className={`text-slate-400 leading-relaxed ${
                        isLarge ? "text-lg" : "text-sm"
                      }`}
                    >
                      {feature.description}
                    </p>
                  </div>
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
