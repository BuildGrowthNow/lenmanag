"use client";

import { motion } from "framer-motion";

export function AnimatedHeroHeadline() {
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.15,
        delayChildren: 0.3,
      },
    },
  };

  const lineVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        duration: 0.8,
        ease: "easeOut",
      },
    },
  };

  const highlightVariants = {
    hidden: { opacity: 0, scale: 0.8 },
    visible: {
      opacity: 1,
      scale: 1,
      transition: {
        duration: 0.6,
        ease: "easeOut",
      },
    },
  };

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="text-center"
    >
      <motion.div variants={lineVariants} className="mb-4">
        <h1 className="text-5xl md:text-7xl font-bold text-white">
          Master
        </h1>
      </motion.div>

      <motion.div variants={lineVariants} className="mb-6">
        <h1 className="text-5xl md:text-7xl font-bold bg-gradient-to-r from-white via-yellow-100 to-white bg-clip-text text-transparent">
          Design
        </h1>
      </motion.div>

      <motion.div
        variants={highlightVariants}
        className="inline-flex items-center gap-3 px-6 py-3 mb-8 bg-gradient-to-r from-yellow-500/10 to-yellow-500/5 border border-yellow-500/30 rounded-full backdrop-blur-sm"
      >
        <span className="text-2xl md:text-3xl font-bold bg-gradient-to-r from-yellow-400 to-yellow-300 bg-clip-text text-transparent">
          $1,000
        </span>
        <span className="text-slate-400">•</span>
        <span className="text-2xl md:text-3xl font-bold bg-gradient-to-r from-yellow-400 to-yellow-300 bg-clip-text text-transparent">
          3 Days
        </span>
      </motion.div>

      <motion.p
        variants={lineVariants}
        className="text-xl md:text-2xl text-slate-300 max-w-3xl mx-auto"
      >
        Premium, custom-crafted websites built by design experts.
        <br className="hidden md:block" />
        <span className="text-yellow-500 font-semibold">
          No compromises. No delays. Just masterfully executed results.
        </span>
      </motion.p>
    </motion.div>
  );
}
