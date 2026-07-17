"use client";

import { motion, AnimatePresence } from "framer-motion";
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
  const [isMobile, setIsMobile] = useState(false);
  const [isVisibleMobile, setIsVisibleMobile] = useState(true);

  useEffect(() => {
    const mq = window.matchMedia("(max-width: 767px)");
    setIsMobile(mq.matches);
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  useEffect(() => {
    let timer: ReturnType<typeof setInterval>;
    let dismissTimer: ReturnType<typeof setTimeout>;

    if (isMobile && isVisibleMobile) {
      dismissTimer = setTimeout(() => {
        setIsVisibleMobile(false);
      }, 3000);
    } else if (!isMobile) {
      timer = setInterval(() => {
        setCurrentIndex((prev) => (prev + 1) % NOTIFICATIONS.length);
      }, 5000);
    }

    return () => {
      clearInterval(timer);
      clearTimeout(dismissTimer);
    };
  }, [isMobile, isVisibleMobile]);

  return (
    <AnimatePresence>
      {isVisibleMobile || !isMobile ? (
        <motion.div
          initial={{ y: 0, opacity: 1 }}
          exit={{ y: -100, opacity: 0 }}
          transition={{ duration: 0.5 }}
          className="relative z-[100] bg-gradient-to-r from-emerald-900 to-blue-900 border-b-2 border-emerald-700 py-2 md:py-4 px-4 md:px-6 shadow-lg"
        >
          <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center md:justify-between gap-3 md:gap-4 items-center md:items-center justify-center md:justify-between">
            {/* Social Proof */}
            <motion.div
              key={currentIndex}
              initial={{ opacity: 0, x: -30 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 30 }}
              transition={{ duration: 0.5 }}
              className="flex items-center gap-2 md:gap-3 text-xs sm:text-sm md:text-base font-bold text-white flex-1 min-w-0 text-center md:text-left justify-center md:justify-start"
            >
              <motion.div
                animate={{ scale: [1, 1.2, 1] }}
                transition={{ duration: 0.6 }}
                className="text-base md:text-lg flex-shrink-0"
              >
                🔥
              </motion.div>
              <span className="flex-shrink-0">{NOTIFICATIONS[currentIndex].name}</span>
              <span className="text-emerald-300 truncate">{NOTIFICATIONS[currentIndex].message}</span>
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
              className="hidden md:flex items-center gap-2 rounded-full bg-red-500/30 px-3 md:px-5 py-1.5 md:py-2 border-2 border-red-500 backdrop-blur-sm flex-shrink-0"
            >
              <motion.div
                animate={{ scale: [1, 1.3, 1] }}
                transition={{ duration: 1, repeat: Infinity, repeatDelay: 1.5 }}
                className="w-2 md:w-3 h-2 md:h-3 rounded-full bg-red-500 shadow-lg"
              />
              <span className="text-xs md:text-sm font-bold text-red-300 whitespace-nowrap">
                Only 3 spots left - book fast! ⏱️
              </span>
            </motion.div>
          </div>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}
