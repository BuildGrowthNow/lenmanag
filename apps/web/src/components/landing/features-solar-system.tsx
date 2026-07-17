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
    position: 0,
  },
  {
    id: "performance",
    title: "Fast Loading",
    description: "Better user experience and improved search rankings",
    icon: Zap,
    orbit: 0,
    position: 1,
  },
  {
    id: "mobile",
    title: "Mobile Ready",
    description: "Works perfectly on phones and tablets for every customer",
    icon: Smartphone,
    orbit: 1,
    position: 0,
  },
  {
    id: "easy",
    title: "Easy to Manage",
    description: "Update your site without coding knowledge required",
    icon: Sliders,
    orbit: 1,
    position: 1,
  },
  {
    id: "support",
    title: "Customer Support",
    description: "Always here when you need help with your website",
    icon: Headphones,
    orbit: 2,
    position: 0,
  },
  {
    id: "quality",
    title: "Professional Quality",
    description: "Trusted by successful businesses worldwide",
    icon: Award,
    orbit: 2,
    position: 1,
  },
  {
    id: "turnaround",
    title: "Quick Turnaround",
    description: "Ready to launch in just 3 days guaranteed",
    icon: Clock,
    orbit: 3,
    position: 0,
  },
  {
    id: "affordable",
    title: "Affordable",
    description: "Enterprise-quality results without premium pricing",
    icon: DollarSign,
    orbit: 3,
    position: 1,
  },
];

const ORBITS = [
  { radius: 120, pointAngle: 0 },
  { radius: 170, pointAngle: 90 },
  { radius: 220, pointAngle: 180 },
  { radius: 270, pointAngle: 270 },
];

export function FeaturesSolarSystem() {
  const [hoveredFeature, setHoveredFeature] = useState<string | null>(null);
  const [isHovering, setIsHovering] = useState(false);

  return (
    <section className="relative px-6 py-24 bg-slate-900/50 overflow-visible">
      <div className="max-w-6xl mx-auto overflow-visible">
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
        <div className="hidden md:flex items-center justify-center overflow-visible" style={{ minHeight: "900px" }}>
          <div className="relative overflow-visible" style={{ width: "700px", height: "700px" }}>
            {/* Center Circle */}
            <motion.div
              initial={{ scale: 0 }}
              whileInView={{ scale: 1 }}
              transition={{ duration: 0.5 }}
              viewport={{ once: true }}
              className="absolute z-0"
              style={{
                left: "294px",
                top: "294px",
              }}
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

            {/* Orbital Rings with Points - Static */}
            <svg
              className="absolute inset-0 w-full h-full pointer-events-none"
              viewBox="0 0 700 700"
            >
              {ORBITS.map((orbit, idx) => {
                const pointX =
                  350 + Math.cos((orbit.pointAngle * Math.PI) / 180) * orbit.radius;
                const pointY =
                  350 + Math.sin((orbit.pointAngle * Math.PI) / 180) * orbit.radius;

                return (
                  <g key={`orbit-${idx}`}>
                    <circle
                      cx="350"
                      cy="350"
                      r={orbit.radius}
                      fill="none"
                      stroke="rgba(255, 255, 255, 0.08)"
                      strokeWidth="1"
                      strokeDasharray="4 6"
                    />
                    <circle
                      cx={pointX}
                      cy={pointY}
                      r="4"
                      fill="rgba(234, 179, 8, 0.4)"
                    />
                  </g>
                );
              })}
            </svg>

            {/* Features on Orbits - Each orbit rotates independently */}
            {ORBITS.map((orbit, orbitIdx) => {
              const isClockwise = orbitIdx % 2 === 0;
              const duration = 60 + orbitIdx * 10;

              return (
                <motion.div
                  key={`orbit-container-${orbitIdx}`}
                  className="absolute inset-0 will-change-transform"
                  style={{
                    left: "50%",
                    top: "50%",
                    width: orbit.radius * 2,
                    height: orbit.radius * 2,
                    marginLeft: -orbit.radius,
                    marginTop: -orbit.radius,
                    zIndex: 10 + orbitIdx,
                    pointerEvents: "none",
                  }}
                  animate={{ rotate: isClockwise ? 360 : -360 }}
                  transition={{
                    duration: duration,
                    repeat: isHovering ? 0 : Infinity,
                    ease: "linear",
                  }}
                >
                  {FEATURES.filter((f) => f.orbit === orbitIdx).map(
                    (feature, indexInOrbit) => {
                      const baseAngle = orbitIdx * 45;
                      const angle = baseAngle + indexInOrbit * 180;
                      const rad = (angle * Math.PI) / 180;
                      const x = orbit.radius + orbit.radius * Math.cos(rad);
                      const y = orbit.radius + orbit.radius * Math.sin(rad);
                      const rotation = isClockwise ? 360 : -360;

                      const isLeftSide = angle > 90 && angle < 270;
                      const isTopSide = angle > 180 && angle < 360;

                      return (
                        <motion.div
                          key={feature.id}
                          className="absolute z-10"
                          animate={{ rotate: -rotation }}
                          transition={{
                            duration: duration,
                            repeat: isHovering ? 0 : Infinity,
                            ease: "linear",
                          }}
                          style={{
                            left: `${x}px`,
                            top: `${y}px`,
                            transform: "translate(-50%, -50%)",
                            pointerEvents: "auto",
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
                          <div className="relative" style={{ pointerEvents: "auto" }}>
                            <button
                              className={`w-16 h-16 rounded-full bg-gradient-to-br from-slate-800 to-slate-900 border-2 shadow-lg flex items-center justify-center cursor-pointer transition-all ${
                                hoveredFeature === feature.id
                                  ? "border-yellow-500 shadow-yellow-500/40"
                                  : "border-white/20 [@media(hover:hover)]:hover:border-yellow-500/60"
                              }`}
                              style={{ pointerEvents: "auto" }}
                            >
                              <feature.icon
                                className={`w-7 h-7 transition-colors ${
                                  hoveredFeature === feature.id
                                    ? "text-yellow-300"
                                    : "text-yellow-500"
                                }`}
                              />
                            </button>

                            {/* Popover - positioned based on quadrant */}
                            {hoveredFeature === feature.id && (
                              <motion.div
                                initial={{ opacity: 0, scale: 0.8 }}
                                animate={{ opacity: 1, scale: 1 }}
                                transition={{ duration: 0.15 }}
                                className="absolute pointer-events-none"
                                style={{
                                  left: isLeftSide ? "auto" : "calc(100% + 12px)",
                                  right: isLeftSide ? "calc(100% + 12px)" : "auto",
                                  top: "50%",
                                  transform: "translateY(-50%)",
                                  whiteSpace: "nowrap",
                                  zIndex: 9999,
                                }}
                              >
                                <div className="px-4 py-3 rounded-xl bg-slate-900/95 border border-yellow-500/50 shadow-xl shadow-yellow-500/20 min-w-[220px] backdrop-blur-sm">
                                  <div className="text-sm font-bold text-yellow-400 mb-1">
                                    {feature.title}
                                  </div>
                                  <div className="text-xs text-slate-300 leading-relaxed whitespace-normal">
                                    {feature.description}
                                  </div>
                                </div>
                              </motion.div>
                            )}
                          </div>
                        </motion.div>
                      );
                    }
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
                className="p-4 rounded-xl bg-white/5 md:backdrop-blur-sm border border-white/10 [@media(hover:hover)]:hover:border-yellow-500/30 md:transition-all group text-center"
              >
                <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-gradient-to-br from-slate-800 to-slate-900 border border-white/20 flex items-center justify-center [@media(hover:hover)]:group-hover:border-yellow-500/50 transition-colors">
                  <Icon className="w-6 h-6 text-yellow-500" />
                </div>
                <h3 className="font-bold text-white text-sm mb-1 [@media(hover:hover)]:group-hover:text-yellow-500 transition-colors">
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
