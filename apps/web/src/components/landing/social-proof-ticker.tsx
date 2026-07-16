"use client";

import { motion } from "framer-motion";
import { useEffect, useState } from "react";

const NOTIFICATIONS = [
  { name: "Sarah M.", message: "just got her dream website live 🎉" },
  { name: "James T.", message: "is getting 10x more leads now 📈" },
  { name: "Emma R.", message: "launched her online store today 🛍️" },
  { name: "Michael K.", message: "can't believe how fast it was ⚡" },
  { name: "Lisa P.", message: "says it's a game-changer for her business 🚀" },
  { name: "David S.", message: "is already seeing results 💰" },
];

export function SocialProofTicker() {
  const [currentIndex, setCurrentIndex] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentIndex((prev) => (prev + 1) % NOTIFICATIONS.length);
    }, 5000);

    return () => clearInterval(timer);
  }, []);

  return (
    <div className="fixed top-0 left-0 right-0 z-[100] bg-gradient-to-r from-yellow-500/95 to-orange-500/95 backdrop-blur-sm border-b-2 border-yellow-300 py-4 px-6 shadow-lg">
      <div className="max-w-7xl mx-auto flex items-center justify-between flex-wrap gap-4">
        {/* Social Proof */}
        <motion.div
          key={currentIndex}
          initial={{ opacity: 0, x: -30 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: 30 }}
          transition={{ duration: 0.5 }}
          className="flex items-center gap-3 text-sm md:text-base font-bold text-zinc-900"
        >
          <motion.div
            animate={{ scale: [1, 1.2, 1] }}
            transition={{ duration: 0.6 }}
            className="text-lg"
          >
            ✨
          </motion.div>
          <span className="hidden sm:inline">{NOTIFICATIONS[currentIndex].name}</span>
          <span className="sm:hidden">Someone</span>
          <span className="text-yellow-700">{NOTIFICATIONS[currentIndex].message}</span>
        </motion.div>

        {/* Scarcity Counter */}
        <motion.div
          animate={{
            scale: [1, 1.08, 1],
            boxShadow: [
              "0 0 0 0 rgba(239, 68, 68, 0.3)",
              "0 0 0 10px rgba(239, 68, 68, 0)",
            ],
          }}
          transition={{
            duration: 1.5,
            repeat: Infinity,
            repeatDelay: 3,
          }}
          className="flex items-center gap-2 rounded-full bg-red-500/30 px-5 py-2 border-2 border-red-500 backdrop-blur-sm"
        >
          <motion.div
            animate={{ scale: [1, 1.3, 1] }}
            transition={{ duration: 1, repeat: Infinity, repeatDelay: 1.5 }}
            className="w-3 h-3 rounded-full bg-red-500 shadow-lg"
          />
          <span className="text-xs md:text-sm font-bold text-red-700">
            Only 3 spots left - book fast! ⏱️
          </span>
        </motion.div>
      </div>
    </div>
  );
}
