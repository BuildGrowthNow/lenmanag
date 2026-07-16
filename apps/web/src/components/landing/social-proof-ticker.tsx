"use client";

import { motion } from "framer-motion";
import { useEffect, useState } from "react";

const NOTIFICATIONS = [
  { name: "Sarah M.", package: "Professional Package", price: "$2,500" },
  { name: "James T.", package: "Basic Website", price: "$1,000" },
  { name: "Emma R.", package: "E-Commerce Site", price: "$3,500" },
  { name: "Michael K.", package: "Professional Package", price: "$2,500" },
  { name: "Lisa P.", package: "Basic Website", price: "$1,000" },
  { name: "David S.", package: "Professional Package", price: "$2,500" },
];

export function SocialProofTicker() {
  const [spotsLeft, setSpotsLeft] = useState(3);
  const [currentIndex, setCurrentIndex] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentIndex((prev) => (prev + 1) % NOTIFICATIONS.length);
    }, 4000);

    return () => clearInterval(timer);
  }, []);

  return (
    <div className="fixed top-0 left-0 right-0 z-40 bg-gradient-to-r from-yellow-500/90 to-orange-500/90 backdrop-blur-sm border-b border-yellow-400/50 py-3 px-6">
      <div className="max-w-7xl mx-auto flex items-center justify-between flex-wrap gap-4">
        {/* Social Proof */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          className="flex items-center gap-2 text-sm font-semibold text-zinc-900"
        >
          <span className="inline-flex items-center gap-2">
            ✨ {NOTIFICATIONS[currentIndex].name} just ordered{" "}
            <span className="text-yellow-700 font-bold">
              {NOTIFICATIONS[currentIndex].package}
            </span>
          </span>
        </motion.div>

        {/* Scarcity Counter */}
        <motion.div
          animate={{
            scale: [1, 1.1, 1],
          }}
          transition={{
            duration: 1,
            repeat: Infinity,
            repeatDelay: 2,
          }}
          className="flex items-center gap-2 rounded-full bg-red-500/20 px-4 py-1.5 border border-red-400/50"
        >
          <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
          <span className="text-xs font-bold text-red-700">
            Only {spotsLeft} spots left this month
          </span>
        </motion.div>
      </div>
    </div>
  );
}
