"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useState, useEffect } from "react";
import { X, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";

interface StickyMessage {
  text: string;
  section: string;
}

const MESSAGES: StickyMessage[] = [
  { text: "See how we create masterpieces", section: "hero" },
  { text: "Only $1,000 to get started", section: "features" },
  { text: "Join 500+ satisfied clients", section: "testimonials" },
  { text: "Lock in your spot now", section: "pricing" },
];

export function StickyCTABar() {
  const [isVisible, setIsVisible] = useState(true);
  const [message, setMessage] = useState(MESSAGES[0]);
  const [showExitIntent, setShowExitIntent] = useState(false);
  const [hasShownExitIntent, setHasShownExitIntent] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      const scrollPercentage = (window.scrollY / document.documentElement.scrollHeight) * 100;

      if (scrollPercentage < 20) {
        setMessage(MESSAGES[0]);
      } else if (scrollPercentage < 40) {
        setMessage(MESSAGES[1]);
      } else if (scrollPercentage < 70) {
        setMessage(MESSAGES[2]);
      } else {
        setMessage(MESSAGES[3]);
      }
    };

    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  useEffect(() => {
    const handleMouseLeave = (e: MouseEvent) => {
      if (
        e.clientY <= 0 &&
        !hasShownExitIntent &&
        window.scrollY > window.innerHeight
      ) {
        setShowExitIntent(true);
        setHasShownExitIntent(true);
        setTimeout(() => setShowExitIntent(false), 10000);
      }
    };

    document.addEventListener("mouseleave", handleMouseLeave);
    return () => document.removeEventListener("mouseleave", handleMouseLeave);
  }, [hasShownExitIntent]);

  const handlePricing = () => {
    document.getElementById("pricing")?.scrollIntoView({ behavior: "smooth" });
    setShowExitIntent(false);
  };

  return (
    <>
      {/* Sticky CTA Bar */}
      <AnimatePresence>
        {isVisible && (
          <motion.div
            initial={{ y: 100, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 100, opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="fixed bottom-0 left-0 right-0 z-30 bg-gradient-to-r from-yellow-500 to-orange-500 backdrop-blur-sm shadow-2xl"
          >
            <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between flex-wrap gap-4">
              <motion.div
                key={message.section}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 10 }}
                transition={{ duration: 0.3 }}
                className="text-sm md:text-base font-bold text-zinc-900"
              >
                ✨ {message.text}
              </motion.div>

              <div className="flex items-center gap-3">
                <motion.button
                  onClick={handlePricing}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  className="px-6 py-2 bg-zinc-900 hover:bg-zinc-800 text-yellow-400 rounded-full font-semibold text-sm transition-all flex items-center gap-2"
                >
                  Get Started
                  <ArrowRight className="w-4 h-4" />
                </motion.button>

                <button
                  onClick={() => setIsVisible(false)}
                  className="p-2 hover:bg-yellow-600 rounded-full transition-colors text-zinc-900"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Exit Intent Modal */}
      <AnimatePresence>
        {showExitIntent && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setShowExitIntent(false)}
            className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-6"
          >
            <motion.div
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.8, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              className="bg-gradient-to-br from-zinc-900 to-zinc-950 rounded-2xl border border-yellow-500/30 p-8 max-w-md text-center shadow-2xl"
            >
              <div className="text-4xl mb-4">🎁</div>

              <h3 className="text-2xl font-bold text-white mb-3">
                Wait! Before you go...
              </h3>

              <p className="text-zinc-300 mb-2">
                Grab <span className="text-yellow-500 font-bold">15% off</span> your next website if you book
                <span className="text-yellow-500 font-bold"> in the next 24 hours</span>
              </p>

              <p className="text-sm text-zinc-400 mb-6">
                Last chance to join our April cohort
              </p>

              <div className="space-y-3">
                <Button
                  onClick={handlePricing}
                  className="w-full px-6 py-3 bg-yellow-500 hover:bg-yellow-600 text-zinc-900 font-bold rounded-lg transition-all"
                >
                  Lock In My Discount
                </Button>

                <button
                  onClick={() => setShowExitIntent(false)}
                  className="w-full px-6 py-2 text-zinc-400 hover:text-white transition-colors text-sm"
                >
                  No thanks, I'll pay full price
                </button>
              </div>

              <div className="mt-6 pt-6 border-t border-white/10">
                <p className="text-xs text-zinc-500">
                  Only 3 spots available at this rate
                </p>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
