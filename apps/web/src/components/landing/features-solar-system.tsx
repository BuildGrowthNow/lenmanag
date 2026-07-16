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
    orbit: 0,
  },
  {
    id: "performance",
    title: "Fast Loading",
    description: "Better user experience and improved search rankings",
    icon: Zap,
    orbit: 0,
  },
  {
    id: "mobile",
    title: "Mobile Ready",
    description: "Works perfectly on phones and tablets for every customer",
    icon: Smartphone,
    orbit: 1,
  },
  {
    id: "easy",
    title: "Easy to Manage",
    description: "Update your site without coding knowledge required",
    icon: Sliders,
    orbit: 1,
  },
  {
    id: "support",
    title: "Customer Support",
    description: "Always here when you need help with your website",
    icon: Headphones,
    orbit: 2,
  },
  {
    id: "quality",
    title: "Professional Quality",
    description: "Trusted by successful businesses worldwide",
    icon: Award,
    orbit: 2,
  },
  {
    id: "turnaround",
    title: "Quick Turnaround",
    description: "Ready to launch in just 3 days guaranteed",
    icon: Clock,
    orbit: 3,
  },
  {
    id: "affordable",
    title: "Affordable",
    description: "Enterprise-quality results without premium pricing",
    icon: DollarSign,
    orbit: 3,
  },
];

const ORBITS = [
  { radius: 140, speed: 20, angle: 0 },
  { radius: 180, speed: 25, angle: 90 },
  { radius: 140, speed: 20, angle: 180 },
  { radius: 180, speed: 25, angle: 270 },
];

export function FeaturesSolarSystem() {
  const [hoveredFeature, setHoveredFeature] = useState<string | null>(null);

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

            {/* Four Orbital Rings with Points */}
            {ORBITS.map((orbit, orbitIdx) => (
              <div key={`orbit-${orbitIdx}`}>
                {/* Orbital Ring SVG */}
                <svg
                  className="absolute inset-0 w-full h-full pointer-events-none"
                  style={{
                    left: "50%",
                    top: "50%",
                    transform: "translate(-50%, -50%)"
                  }}
                  viewBox="0 0 700 700"
                >
                  <circle
                    cx="350"
                    cy="350"
                    r={orbit.radius}
                    fill="none"
                    stroke="rgba(255, 255, 255, 0.1)"
                    strokeWidth="1"
                    strokeDasharray="4 6"
                  />
                  {/* Point indicator on orbit */}
                  <circle
                    cx={350 + Math.cos((orbit.angle * Math.PI) / 180) * orbit.radius}
                    cy={350 + Math.sin((orbit.angle * Math.PI) / 180) * orbit.radius}
                    r="4"
                    fill="rgba(234, 179, 8, 0.3)"
                  />
                </svg>

                {/* Features orbiting on this ring */}
                {FEATURES.filter((f) => f.orbit === orbitIdx).map(
                  (feature, indexInOrbit) => {
                    const totalInOrbit = FEATURES.filter(
                      (f) => f.orbit === orbitIdx
                    ).length;
                    const offset = indexInOrbit * (360 / totalInOrbit);

                    return (
                      <motion.div
                        key={feature.id}
                        className="absolute"
                        initial={{ opacity: 0, scale: 0 }}
                        animate={{ opacity: 1, scale: 1, rotate: 360 }}
                        transition={{
                          opacity: {
                            delay: orbitIdx * 0.2 + indexInOrbit * 0.1,
                            duration: 0.5,
                          },
                          scale: {
                            delay: orbitIdx * 0.2 + indexInOrbit * 0.1,
                            duration: 0.5,
                          },
                          rotate: {
                            duration: orbit.speed,
                            repeat: Infinity,
                            ease: "linear",
                          },
                        }}
                        viewport={{ once: true }}
                        style={{
                          left: "50%",
                          top: "50%",
                          width: orbit.radius * 2,
                          height: orbit.radius * 2,
                          marginLeft: -orbit.radius,
                          marginTop: -orbit.radius,
                        }}
                      >
                        <motion.div
                          className="absolute"
                          style={{
                            left: "50%",
                            top: "0%",
                            transform: `rotate(${offset}deg) translateX(${orbit.radius}px)`,
                            transformOrigin: "0 0",
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
                            onMouseEnter={() => setHoveredFeature(feature.id)}
                            onMouseLeave={() => setHoveredFeature(null)}
                          >
                            <feature.icon
                              className={`w-7 h-7 transition-colors ${
                                hoveredFeature === feature.id
                                  ? "text-yellow-300"
                                  : "text-yellow-500"
                              }`}
                            />
                          </motion.button>

                          {/* Popover on Hover */}
                          {hoveredFeature === feature.id && (
                            <motion.div
                              initial={{ opacity: 0, scale: 0.8 }}
                              animate={{ opacity: 1, scale: 1 }}
                              transition={{ duration: 0.15 }}
                              className="absolute z-50 pointer-events-none whitespace-nowrap"
                              style={{
                                top: "-80px",
                                left: "-110px",
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
                      </motion.div>
                    );
                  }
                )}
              </div>
            ))}
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
