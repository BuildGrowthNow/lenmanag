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
    line: 0,
    position: 0,
  },
  {
    id: "performance",
    title: "Fast Loading",
    description: "Better user experience and improved search rankings",
    icon: Zap,
    line: 0,
    position: 1,
  },
  {
    id: "mobile",
    title: "Mobile Ready",
    description: "Works perfectly on phones and tablets for every customer",
    icon: Smartphone,
    line: 1,
    position: 0,
  },
  {
    id: "easy",
    title: "Easy to Manage",
    description: "Update your site without coding knowledge required",
    icon: Sliders,
    line: 1,
    position: 1,
  },
  {
    id: "support",
    title: "Customer Support",
    description: "Always here when you need help with your website",
    icon: Headphones,
    line: 2,
    position: 0,
  },
  {
    id: "quality",
    title: "Professional Quality",
    description: "Trusted by successful businesses worldwide",
    icon: Award,
    line: 2,
    position: 1,
  },
  {
    id: "turnaround",
    title: "Quick Turnaround",
    description: "Ready to launch in just 3 days guaranteed",
    icon: Clock,
    line: 3,
    position: 0,
  },
  {
    id: "affordable",
    title: "Affordable",
    description: "Enterprise-quality results without premium pricing",
    icon: DollarSign,
    line: 3,
    position: 1,
  },
];

const LINES = [
  { angle: 0, label: "top" },
  { angle: 90, label: "right" },
  { angle: 180, label: "bottom" },
  { angle: 270, label: "left" },
];

export function FeaturesSolarSystem() {
  const [hoveredFeature, setHoveredFeature] = useState<string | null>(null);
  const [isHovering, setIsHovering] = useState(false);

  return (
    <section className="relative px-6 py-24 bg-slate-900/50 overflow-visible">
      <div className="max-w-6xl mx-auto">
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
            Everything for your online presence
          </p>
        </motion.div>

        {/* Solar System Visualization - Desktop */}
        <div className="hidden md:flex items-center justify-center">
          <div className="relative" style={{ width: "700px", height: "700px" }}>
            {/* Center Circle */}
            <motion.div
              initial={{ scale: 0 }}
              whileInView={{ scale: 1 }}
              transition={{ duration: 0.5 }}
              viewport={{ once: true }}
              className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-20"
            >
              <motion.div
                animate={{ scale: [1, 1.05, 1] }}
                transition={{ duration: 3, repeat: Infinity }}
                className="w-28 h-28 rounded-full bg-gradient-to-br from-yellow-500 to-yellow-600 flex items-center justify-center shadow-2xl shadow-yellow-500/50"
              >
                <div className="text-center px-3">
                  <div className="text-xs font-bold text-slate-900 leading-tight">
                    Your Website
                  </div>
                </div>
              </motion.div>
            </motion.div>

            {/* Four pointing lines */}
            <svg
              className="absolute inset-0 w-full h-full pointer-events-none"
              viewBox="0 0 700 700"
            >
              {LINES.map((line, idx) => {
                const x1 = 350;
                const y1 = 350;
                const x2 = 350 + Math.cos((line.angle * Math.PI) / 180) * 280;
                const y2 = 350 + Math.sin((line.angle * Math.PI) / 180) * 280;

                return (
                  <g key={`line-${idx}`}>
                    <line
                      x1={x1}
                      y1={y1}
                      x2={x2}
                      y2={y2}
                      stroke="rgba(255, 255, 255, 0.1)"
                      strokeWidth="1"
                      strokeDasharray="4 6"
                    />
                    <circle
                      cx={x2}
                      cy={y2}
                      r="4"
                      fill="rgba(234, 179, 8, 0.4)"
                    />
                  </g>
                );
              })}
            </svg>

            {/* Orbiting features on all lines */}
            {FEATURES.map((feature, idx) => {
              const line = LINES[feature.line];
              const angle = (line.angle * Math.PI) / 180;
              const isOdd = feature.position === 1;

              return (
                <motion.div
                  key={feature.id}
                  className="absolute"
                  initial={{ opacity: 0, scale: 0 }}
                  whileInView={{ opacity: 1, scale: 1 }}
                  transition={{
                    delay: idx * 0.05,
                    duration: 0.5,
                  }}
                  viewport={{ once: true }}
                  animate={
                    isHovering
                      ? {}
                      : {
                          x: isOdd
                            ? [
                                Math.cos(angle) * 150,
                                Math.cos(angle) * 280,
                                Math.cos(angle) * 150,
                              ]
                            : [
                                Math.cos(angle) * 280,
                                Math.cos(angle) * 150,
                                Math.cos(angle) * 280,
                              ],
                          y: isOdd
                            ? [
                                Math.sin(angle) * 150,
                                Math.sin(angle) * 280,
                                Math.sin(angle) * 150,
                              ]
                            : [
                                Math.sin(angle) * 280,
                                Math.sin(angle) * 150,
                                Math.sin(angle) * 280,
                              ],
                        }
                  }
                  transition={{
                    duration: 6,
                    repeat: Infinity,
                    ease: "easeInOut",
                  }}
                  style={{
                    left: "350px",
                    top: "350px",
                    transform: "translate(-50%, -50%)",
                  }}
                  onMouseEnter={() => {
                    setHoveredFeature(feature.id);
                    setIsHovering(true);
                  }}
                  onMouseLeave={() => {
                    setHoveredFeature(null);
                    setIsHovering(false);
                  }}
                >
                  <motion.button
                    whileHover={{ scale: 1.2 }}
                    whileTap={{ scale: 0.95 }}
                    className={`w-16 h-16 rounded-full bg-gradient-to-br from-slate-800 to-slate-900 border-2 shadow-lg flex items-center justify-center cursor-pointer transition-all ${
                      hoveredFeature === feature.id
                        ? "border-yellow-500 shadow-yellow-500/40"
                        : "border-white/20 hover:border-yellow-500/60"
                    }`}
                  >
                    <feature.icon
                      className={`w-7 h-7 transition-colors ${
                        hoveredFeature === feature.id
                          ? "text-yellow-300"
                          : "text-yellow-500"
                      }`}
                    />
                  </motion.button>

                  {/* Popover on Hover - horizontal, not rotated */}
                  {hoveredFeature === feature.id && (
                    <motion.div
                      initial={{ opacity: 0, scale: 0.8, x: -10 }}
                      animate={{ opacity: 1, scale: 1, x: 0 }}
                      transition={{ duration: 0.15 }}
                      className="absolute z-50 pointer-events-none"
                      style={{
                        left: "100%",
                        top: "50%",
                        transform: "translateY(-50%)",
                        marginLeft: "12px",
                      }}
                    >
                      <div className="px-4 py-3 rounded-xl bg-slate-900/95 border border-yellow-500/50 shadow-xl shadow-yellow-500/20 min-w-[220px] backdrop-blur-sm">
                        <div className="text-sm font-bold text-yellow-400 mb-1">
                          {feature.title}
                        </div>
                        <div className="text-xs text-slate-300 leading-relaxed">
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

        {/* Mobile View - Grid Layout */}
        <div className="md:hidden grid grid-cols-2 gap-4 mt-8">
          {FEATURES.map((feature, i) => {
            const Icon = feature.icon;
            return (
              <motion.div
                key={feature.id}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05, duration: 0.4 }}
                viewport={{ once: true }}
                className="p-4 rounded-xl bg-white/5 backdrop-blur-sm border border-white/10 hover:border-yellow-500/30 transition-all group text-center"
              >
                <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-gradient-to-br from-slate-800 to-slate-900 border border-white/20 flex items-center justify-center group-hover:border-yellow-500/50 transition-colors">
                  <Icon className="w-6 h-6 text-yellow-500" />
                </div>
                <h3 className="font-bold text-white text-sm mb-1 group-hover:text-yellow-500 transition-colors">
                  {feature.title}
                </h3>
                <p className="text-xs text-slate-400">
                  {feature.description}
                </p>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
