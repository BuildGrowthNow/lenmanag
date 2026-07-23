"use client";

import { motion } from "framer-motion";
import {
  CheckCircle2,
  Star,
  Calendar,
  Shield,
  ArrowRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useSupportsHover } from "@/hooks/use-supports-hover";

const INCLUDED = [
  "Complete landing page built for your brand",
  "Works perfectly on phones and tablets",
  "Loads fast so customers don't wait",
  "Found easily on Google search",
  "Secure and trusted by visitors",
  "Easy way for customers to contact you",
  "Full ownership of all code and assets",
  "Delivered ready to go live",
  "7 days of post-launch support included",
];

export function PricingConfigurator() {
  const supportsHover = useSupportsHover();

  return (
    <div className="w-full">
      <div className="text-center mb-10">
        <motion.div
          initial={{ scale: 0.9, opacity: 0 }}
          whileInView={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.5 }}
          viewport={{ once: true }}
          className="inline-flex items-center gap-2 px-4 py-2 mb-6 bg-yellow-500 rounded-full"
        >
          <Star className="w-4 h-4 text-slate-900" />
          <span className="text-sm font-bold text-slate-900">SIMPLE PRICING</span>
        </motion.div>

        <h2 className="text-4xl md:text-5xl font-bold mb-3 text-white">
          One Price. <span className="text-yellow-500">Everything Included.</span>
        </h2>
        <p className="text-lg text-slate-400 max-w-2xl mx-auto">
          A complete landing page delivered in 3 days. No hidden fees, no surprises.
        </p>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        viewport={{ once: true }}
        className="max-w-2xl mx-auto"
      >
        <div className="relative p-8 md:p-10 rounded-3xl bg-gradient-to-br from-slate-800/80 to-slate-900/80 border border-yellow-500/30 backdrop-blur-xl shadow-2xl shadow-yellow-500/10">
          <div className="absolute inset-0 rounded-3xl bg-yellow-500/5 pointer-events-none" />

          <div className="flex items-center justify-between mb-8">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 text-xs font-bold uppercase rounded-full bg-yellow-500/20 text-yellow-500">
              ONE-TIME
            </span>
            <span className="inline-flex items-center gap-1.5 px-3 py-1 text-xs font-bold uppercase rounded-full bg-green-500/20 text-green-400">
              100% Money-Back Guarantee
            </span>
          </div>

          <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4 mb-8">
            <div>
              <h3 className="text-2xl md:text-3xl font-bold text-white mb-1">
                Professional Landing Page
              </h3>
              <p className="text-slate-400">Delivered in 3 days, built for your business</p>
            </div>
            <div className="text-left md:text-right">
              <div className="text-4xl md:text-5xl font-bold text-yellow-500">$1,000</div>
              <div className="text-sm text-slate-400">one-time payment</div>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-8">
            {INCLUDED.map((item, i) => (
              <div key={i} className="flex items-start gap-3">
                <CheckCircle2 className="w-5 h-5 text-yellow-500 flex-shrink-0 mt-0.5" />
                <span className="text-white text-sm">{item}</span>
              </div>
            ))}
          </div>

          <motion.div
            {...(supportsHover && { whileHover: { scale: 1.02 } })}
            whileTap={{ scale: 0.98 }}
          >
            <Button
              onClick={() => window.open("https://calendly.com/lenquant/sites", "_blank")}
              className="w-full py-6 text-lg font-bold bg-yellow-500 hover:bg-yellow-600 text-slate-900 rounded-xl shadow-2xl shadow-yellow-500/50 transition-all"
            >
              <Calendar className="mr-2 w-5 h-5" />
              Book Your Free Call
              <ArrowRight className="ml-2 w-5 h-5" />
            </Button>
          </motion.div>

          <p className="text-center text-xs text-slate-500 mt-4 flex items-center justify-center gap-1.5">
            <Shield className="w-3.5 h-3.5" />
            Free 30-minute call · No commitment · We scope everything together
          </p>
        </div>

        <motion.p
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          transition={{ delay: 0.3, duration: 0.5 }}
          viewport={{ once: true }}
          className="text-center text-slate-500 text-sm mt-6"
        >
          Need extra pages or specific features?{" "}
          <span className="text-slate-300">We&apos;ll scope it together on the call.</span>
        </motion.p>
      </motion.div>
    </div>
  );
}
