"use client";

import { motion } from "framer-motion";
import { Monitor, Smartphone } from "lucide-react";

export function FloatingMockup() {
  return (
    <div className="relative w-full max-w-5xl mx-auto mt-16 h-[400px]">
      {/* Desktop Mockup */}
      <motion.div
        initial={{ opacity: 0, y: 50, rotateX: 20 }}
        animate={{ opacity: 1, y: 0, rotateX: 0 }}
        transition={{ delay: 0.3, duration: 1 }}
        className="absolute left-1/2 top-0 -translate-x-1/2 z-20"
        style={{ perspective: 1200 }}
      >
        <motion.div
          animate={{
            y: [0, -20, 0],
          }}
          transition={{
            duration: 6,
            repeat: Infinity,
            ease: "easeInOut",
          }}
          className="relative"
        >
          <div className="w-[500px] h-[300px] bg-gradient-to-br from-slate-800 to-slate-900 rounded-2xl border-4 border-slate-700 shadow-2xl overflow-hidden">
            {/* Browser Chrome */}
            <div className="h-8 bg-slate-700 flex items-center px-3 gap-2 border-b border-slate-600">
              <div className="flex gap-1.5">
                <div className="w-3 h-3 rounded-full bg-red-500" />
                <div className="w-3 h-3 rounded-full bg-yellow-500" />
                <div className="w-3 h-3 rounded-full bg-green-500" />
              </div>
            </div>
            {/* Content Preview */}
            <div className="p-8 bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
              <div className="h-4 bg-yellow-500/30 rounded w-3/4 mb-4" />
              <div className="h-3 bg-white/10 rounded w-full mb-2" />
              <div className="h-3 bg-white/10 rounded w-5/6 mb-2" />
              <div className="h-3 bg-white/10 rounded w-4/6" />
              <div className="mt-6 flex gap-2">
                <div className="h-8 w-24 bg-yellow-500/50 rounded" />
                <div className="h-8 w-24 bg-white/10 rounded" />
              </div>
            </div>
          </div>
          <Monitor className="absolute -bottom-2 left-1/2 -translate-x-1/2 w-6 h-6 text-slate-600" />
        </motion.div>
      </motion.div>

      {/* Mobile Mockup */}
      <motion.div
        initial={{ opacity: 0, x: 100, rotateY: -20 }}
        animate={{ opacity: 1, x: 0, rotateY: 0 }}
        transition={{ delay: 0.6, duration: 1 }}
        className="absolute right-8 top-20 z-10"
      >
        <motion.div
          animate={{
            y: [0, 15, 0],
          }}
          transition={{
            duration: 5,
            repeat: Infinity,
            ease: "easeInOut",
            delay: 1,
          }}
        >
          <div className="w-[140px] h-[280px] bg-gradient-to-br from-slate-800 to-slate-900 rounded-3xl border-4 border-slate-700 shadow-2xl overflow-hidden p-2">
            {/* Screen */}
            <div className="w-full h-full bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 rounded-2xl p-4 overflow-hidden">
              <div className="h-2 bg-yellow-500/30 rounded w-2/3 mb-3" />
              <div className="h-1.5 bg-white/10 rounded w-full mb-1.5" />
              <div className="h-1.5 bg-white/10 rounded w-4/5 mb-1.5" />
              <div className="h-1.5 bg-white/10 rounded w-3/5 mb-4" />
              <div className="h-6 bg-yellow-500/50 rounded w-full mb-2" />
              <div className="h-6 bg-white/10 rounded w-full" />
            </div>
          </div>
          <Smartphone className="absolute -bottom-1 left-1/2 -translate-x-1/2 w-4 h-4 text-slate-600" />
        </motion.div>
      </motion.div>

      {/* Tablet Mockup */}
      <motion.div
        initial={{ opacity: 0, x: -100, rotateY: 20 }}
        animate={{ opacity: 1, x: 0, rotateY: 0 }}
        transition={{ delay: 0.8, duration: 1 }}
        className="absolute left-8 top-32 z-10"
      >
        <motion.div
          animate={{
            y: [0, -15, 0],
          }}
          transition={{
            duration: 5.5,
            repeat: Infinity,
            ease: "easeInOut",
            delay: 0.5,
          }}
        >
          <div className="w-[180px] h-[240px] bg-gradient-to-br from-slate-800 to-slate-900 rounded-2xl border-4 border-slate-700 shadow-2xl overflow-hidden p-2">
            <div className="w-full h-full bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 rounded-xl p-5 overflow-hidden">
              <div className="h-3 bg-yellow-500/30 rounded w-3/4 mb-3" />
              <div className="h-2 bg-white/10 rounded w-full mb-1.5" />
              <div className="h-2 bg-white/10 rounded w-5/6 mb-1.5" />
              <div className="h-2 bg-white/10 rounded w-4/6 mb-4" />
              <div className="h-7 bg-yellow-500/50 rounded w-full mb-2" />
              <div className="h-7 bg-white/10 rounded w-full" />
            </div>
          </div>
        </motion.div>
      </motion.div>

      {/* Glow Effects */}
      <div className="absolute inset-0 bg-gradient-to-r from-yellow-500/5 via-transparent to-transparent blur-3xl" />
    </div>
  );
}
