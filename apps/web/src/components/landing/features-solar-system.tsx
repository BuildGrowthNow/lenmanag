"use client";

import { motion } from "framer-motion";
import { useState } from "react";
import {
  Palette,
  Zap,
  Smartphone,
  Sliders,
  Headphones,
  Award,
  Clock,
  DollarSign,
} from "lucide-react";

const FEATURES = [
  {
    id: "design",
    title: "Beautiful Design",
    description: "Visual appeal that captivates your visitors and builds trust",
    icon: Palette,
  },
  {
    id: "performance",
    title: "Fast Loading",
    description: "Better user experience and improved search rankings",
    icon: Zap,
  },
  {
    id: "mobile",
    title: "Mobile Ready",
    description: "Works perfectly on phones and tablets for every customer",
    icon: Smartphone,
  },
  {
    id: "easy",
    title: "Easy to Manage",
    description: "Update your site without coding knowledge required",
    icon: Sliders,
  },
  {
    id: "support",
    title: "Customer Support",
    description: "Always here when you need help with your website",
    icon: Headphones,
  },
  {
    id: "quality",
    title: "Professional Quality",
    description: "Trusted by successful businesses worldwide",
    icon: Award,
  },
  {
    id: "turnaround",
    title: "Quick Turnaround",
    description: "Ready to launch in just 3 days guaranteed",
    icon: Clock,
  },
  {
    id: "affordable",
    title: "Affordable",
    description: "Enterprise-quality results without premium pricing",
    icon: DollarSign,
  },
];

const ANGLE_STEP = 360 / FEATURES.length;
const RADIUS = 200;

export function FeaturesSolarSystem() {
  const [hoveredFeature, setHoveredFeature] = useState<string | null>(null);

  return (
    <section className="relative px-6 py-24 bg-slate-900/50">
      <div className="max-w-6xl mx-auto">
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          transition={{ duration: 0.8 }}
          viewport={{ once: true }}
          className="text-center mb-24"
        >
          <h2 className="text-5xl font-bold mb-4">
            Everything You <span className="text-yellow-500">Need</span>
          </h2>
          <p className="text-xl text-slate-400">
            Everything for your online presence
          </p>
        </motion.div>

        {/* Solar System Visualization */}
        <div className="flex items-center justify-center">
          <div className="relative w-full max-w-2xl aspect-square">
            {/* Orbital Rings */}
            <svg
              className="absolute inset-0 w-full h-full pointer-events-none"
              viewBox="0 0 500 500"
            >
              <circle
                cx="250"
                cy="250"
                r="150"
                fill="none"
                stroke="rgba(255, 255, 255, 0.05)"
                strokeWidth="1"
              />
              <circle
                cx="250"
                cy="250"
                r="100"
                fill="none"
                stroke="rgba(255, 255, 255, 0.03)"
                strokeWidth="1"
              />
            </svg>

            {/* Center Circle */}
            <motion.div
              initial={{ scale: 0 }}
              whileInView={{ scale: 1 }}
              transition={{ duration: 0.5 }}
              viewport={{ once: true }}
              className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-10"
            >
              <motion.div
                animate={{ scale: [1, 1.05, 1] }}
                transition={{ duration: 3, repeat: Infinity }}
                className="w-24 h-24 rounded-full bg-gradient-to-br from-yellow-500 to-yellow-600 flex items-center justify-center shadow-2xl shadow-yellow-500/50"
              >
                <div className="text-center px-4">
                  <div className="text-xs font-semibold text-slate-900 leading-tight">
                    Everything You Need
                  </div>
                </div>
              </motion.div>
            </motion.div>

            {/* Orbiting Features */}
            <div className="absolute inset-0 flex items-center justify-center">
              {FEATURES.map((feature, index) => {
                const angle = (ANGLE_STEP * index - 90) * (Math.PI / 180);
                const x = Math.cos(angle) * RADIUS;
                const y = Math.sin(angle) * RADIUS;

                return (
                  <motion.div
                    key={feature.id}
                    className="absolute"
                    initial={{ opacity: 0, scale: 0 }}
                    whileInView={{ opacity: 1, scale: 1 }}
                    transition={{
                      delay: index * 0.1,
                      duration: 0.5,
                    }}
                    viewport={{ once: true }}
                    style={{
                      transform: `translate(calc(-50% + ${x}px), calc(-50% + ${y}px))`,
                    }}
                    onMouseEnter={() => setHoveredFeature(feature.id)}
                    onMouseLeave={() => setHoveredFeature(null)}
                  >
                    <motion.button
                      whileHover={{ scale: 1.1 }}
                      whileTap={{ scale: 0.95 }}
                      className="w-16 h-16 rounded-full bg-gradient-to-br from-slate-800 to-slate-900 border-2 border-white/20 hover:border-yellow-500 shadow-lg flex items-center justify-center cursor-pointer transition-all group"
                    >
                      <feature.icon className="w-8 h-8 text-yellow-500 group-hover:text-yellow-300 transition-colors" />
                    </motion.button>

                    {/* Popover */}
                    {hoveredFeature === feature.id && (
                      <motion.div
                        initial={{ opacity: 0, scale: 0.8 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.8 }}
                        transition={{ duration: 0.2 }}
                        className="absolute top-24 left-1/2 -translate-x-1/2 whitespace-nowrap z-20"
                      >
                        <div className="px-4 py-3 rounded-lg bg-slate-900 border border-yellow-500/50 shadow-xl">
                          <div className="text-sm font-bold text-yellow-500 mb-1">
                            {feature.title}
                          </div>
                          <div className="text-xs text-slate-300 max-w-xs">
                            {feature.description}
                          </div>
                        </div>
                      </motion.div>
                    )}
                  </motion.div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Mobile View - Grid Layout */}
        <div className="lg:hidden grid grid-cols-1 md:grid-cols-2 gap-6 mt-12">
          {FEATURES.map((feature, i) => {
            const Icon = feature.icon;
            return (
              <motion.div
                key={feature.id}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.1, duration: 0.5 }}
                viewport={{ once: true }}
                className="p-6 rounded-xl bg-white/5 backdrop-blur-sm border border-white/10 hover:border-yellow-500/30 transition-all group"
              >
                <div className="flex items-start gap-4">
                  <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-yellow-500 to-yellow-600 flex items-center justify-center flex-shrink-0">
                    <Icon className="w-6 h-6 text-slate-900" />
                  </div>
                  <div>
                    <h3 className="font-bold text-white mb-1 group-hover:text-yellow-500 transition-colors">
                      {feature.title}
                    </h3>
                    <p className="text-sm text-slate-400">
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
