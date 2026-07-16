"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  CheckCircle2,
  Zap,
  ChevronDown,
  Star,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  MAIN_PACKAGE,
  EXTRA_SERVICES,
  type SelectedAddOns,
} from "@/lib/pricing";

interface PricingConfiguratorProps {
  onCheckout: (addOns: SelectedAddOns) => void;
  isLoading: boolean;
}

export function PricingConfigurator({ onCheckout, isLoading }: PricingConfiguratorProps) {
  const [showExtras, setShowExtras] = useState(false);

  return (
    <div className="w-full">
      {/* Header */}
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
          Professional website delivered in 3 days. No hidden fees.
        </p>
      </div>

      {/* Main Package Card */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        viewport={{ once: true }}
        className="max-w-2xl mx-auto mb-8"
      >
        <div className="relative p-8 md:p-10 rounded-3xl bg-gradient-to-br from-slate-800/80 to-slate-900/80 border border-yellow-500/30 backdrop-blur-xl shadow-2xl shadow-yellow-500/10">
          {/* Glow effect */}
          <div className="absolute inset-0 rounded-3xl bg-yellow-500/5 pointer-events-none" />

          {/* Badge */}
          <div className="flex items-center justify-between mb-6">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 text-xs font-bold uppercase rounded-full bg-yellow-500/20 text-yellow-500">
              ONE-TIME
            </span>
            {MAIN_PACKAGE.highlight && (
              <span className="inline-flex items-center gap-1.5 px-3 py-1 text-xs font-bold uppercase rounded-full bg-green-500/20 text-green-400">
                Most Popular
              </span>
            )}
          </div>

          {/* Title & Price */}
          <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4 mb-8">
            <div>
              <h3 className="text-2xl md:text-3xl font-bold text-white mb-1">
                {MAIN_PACKAGE.name}
              </h3>
              <p className="text-slate-400">{MAIN_PACKAGE.description}</p>
            </div>
            <div className="text-right">
              <div className="text-4xl md:text-5xl font-bold text-white">
                ${MAIN_PACKAGE.price.toLocaleString()}
              </div>
              <div className="text-sm text-slate-400">one-time payment</div>
            </div>
          </div>

          {/* Features */}
          <div className="grid sm:grid-cols-2 gap-3 mb-8">
            {MAIN_PACKAGE.features.map((feature, i) => (
              <div key={i} className="flex items-center gap-3">
                <CheckCircle2 className="w-5 h-5 text-yellow-500 flex-shrink-0" />
                <span className="text-white">{feature.text}</span>
              </div>
            ))}
          </div>

          {/* CTA */}
          <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
            <Button
              onClick={() => onCheckout({})}
              disabled={isLoading}
              className="w-full py-6 text-lg font-bold bg-yellow-500 hover:bg-yellow-600 text-slate-900 rounded-xl shadow-2xl shadow-yellow-500/50 transition-all disabled:opacity-50"
            >
              {isLoading ? (
                "Processing..."
              ) : (
                <>
                  <Zap className="mr-2 w-5 h-5" />
                  Get Started Now
                </>
              )}
            </Button>
          </motion.div>

          <p className="text-center text-xs text-slate-500 mt-4">
            Secure payment via Stripe. Money-back guarantee.
          </p>
        </div>
      </motion.div>

      {/* Extra Services Dropdown */}
      <div className="max-w-2xl mx-auto">
        <button
          onClick={() => setShowExtras(!showExtras)}
          className="w-full flex items-center justify-between p-5 rounded-2xl bg-white/5 border border-white/10 hover:border-white/20 transition-all"
        >
          <span className="text-lg font-semibold text-white">Extra Services</span>
          <motion.div
            animate={{ rotate: showExtras ? 180 : 0 }}
            transition={{ duration: 0.3 }}
          >
            <ChevronDown className="w-5 h-5 text-slate-400" />
          </motion.div>
        </button>

        <AnimatePresence>
          {showExtras && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.3 }}
              className="overflow-hidden"
            >
              <div className="pt-4 space-y-4">
                {EXTRA_SERVICES.map((service) => (
                  <div
                    key={service.id}
                    className="p-5 rounded-2xl bg-white/5 border border-white/10"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <div className="flex items-center gap-3">
                          <h4 className="font-semibold text-white">{service.name}</h4>
                          <span
                            className={`inline-flex items-center px-2 py-0.5 text-[10px] font-bold uppercase rounded-full ${
                              service.billingCycle === "monthly"
                                ? "bg-blue-500/20 text-blue-400"
                                : "bg-green-500/20 text-green-400"
                            }`}
                          >
                            {service.billingCycle === "monthly" ? "MONTHLY" : "ONE-TIME"}
                          </span>
                        </div>
                        <p className="text-sm text-slate-400 mt-1">{service.description}</p>
                      </div>
                      <div className="text-right flex-shrink-0 ml-4">
                        <div className="text-xl font-bold text-white">
                          ${service.price}
                        </div>
                        <div className="text-xs text-slate-500">
                          {service.billingCycle === "monthly" ? "/month" : "per page"}
                        </div>
                      </div>
                    </div>

                    <div className="space-y-2">
                      {service.features.map((feature, i) => (
                        <div key={i} className="flex items-center gap-2">
                          <CheckCircle2 className="w-4 h-4 text-yellow-500 flex-shrink-0" />
                          <span className="text-sm text-slate-300">{feature.text}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
