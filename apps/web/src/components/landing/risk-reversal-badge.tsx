"use client";

import { motion } from "framer-motion";
import { Shield, CheckCircle2 } from "lucide-react";
import { useState } from "react";

export function RiskReversalBadge() {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <>
      {/* Floating Badge - Follows on Scroll - Hidden on Mobile */}
      <motion.div
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 1 }}
        className="hidden md:block fixed left-6 bottom-6 z-20 max-w-xs"
      >
        <motion.button
          onClick={() => setIsExpanded(!isExpanded)}
          whileHover={{ scale: 1.05 }}
          className="w-full p-4 rounded-xl bg-gradient-to-r from-green-500/20 to-emerald-500/20 border border-green-500/50 backdrop-blur-sm shadow-lg hover:shadow-xl transition-all"
        >
          <div className="flex items-center gap-3">
            <motion.div
              animate={{ rotate: [0, 10, -10, 0] }}
              transition={{ duration: 2, repeat: Infinity }}
            >
              <Shield className="w-5 h-5 text-green-400 flex-shrink-0" />
            </motion.div>
            <div className="text-left">
              <div className="text-xs font-bold text-green-400 uppercase">
                Zero Risk 🎯
              </div>
              <div className="text-sm font-semibold text-white">
                Get your money back if you&apos;re not thrilled
              </div>
            </div>
          </div>

          {isExpanded && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="mt-3 pt-3 border-t border-green-500/30 space-y-3 text-left"
            >
              <motion.div
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.1 }}
                className="flex items-start gap-2 text-sm text-zinc-200"
              >
                <CheckCircle2 className="w-4 h-4 text-green-400 flex-shrink-0 mt-0.5 flex-shrink-0" />
                <span>7 full days to review. Not happy? Full refund, no questions asked.</span>
              </motion.div>
              <motion.div
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.2 }}
                className="flex items-start gap-2 text-sm text-zinc-200"
              >
                <CheckCircle2 className="w-4 h-4 text-green-400 flex-shrink-0 mt-0.5 flex-shrink-0" />
                <span>Tell us your goal, we handle the rest.</span>
              </motion.div>
              <motion.div
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.3 }}
                className="flex items-start gap-2 text-sm text-zinc-200"
              >
                <CheckCircle2 className="w-4 h-4 text-green-400 flex-shrink-0 mt-0.5 flex-shrink-0" />
                <span>100% satisfaction or your money back. Your investment is protected.</span>
              </motion.div>
            </motion.div>
          )}
        </motion.button>
      </motion.div>

    </>
  );
}
