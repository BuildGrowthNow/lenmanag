"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  CheckCircle2,
  Plus,
  Minus,
  Zap,
  Globe,
  Search,
  FileText,
  BarChart3,
  Rocket,
  Star,
  Clock,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  ADD_ONS,
  BASE_PRICE,
  calculateTotal,
  type SelectedAddOns,
  type AddOn,
} from "@/lib/pricing";

const ADDON_ICONS: Record<string, React.ElementType> = {
  extra_pages: FileText,
  custom_domain: Globe,
  advanced_seo: Search,
  blog_cms: FileText,
  analytics_tracking: BarChart3,
  priority_delivery: Rocket,
};

interface PricingConfiguratorProps {
  onCheckout: (addOns: SelectedAddOns) => void;
  isLoading: boolean;
}

export function PricingConfigurator({ onCheckout, isLoading }: PricingConfiguratorProps) {
  const [selectedAddOns, setSelectedAddOns] = useState<SelectedAddOns>({});
  const total = calculateTotal(selectedAddOns);

  function toggleAddon(addon: AddOn) {
    setSelectedAddOns((prev) => {
      const current = prev[addon.id] || 0;
      if (addon.type === "toggle") {
        return { ...prev, [addon.id]: current > 0 ? 0 : 1 };
      }
      return prev;
    });
  }

  function setQuantity(addonId: string, qty: number) {
    setSelectedAddOns((prev) => ({ ...prev, [addonId]: Math.max(0, qty) }));
  }

  const deliveryDays = selectedAddOns["priority_delivery"] ? 1 : 3;
  const totalPages = 1 + (selectedAddOns["extra_pages"] || 0);

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
          <span className="text-sm font-bold text-slate-900">BUILD YOUR PACKAGE</span>
        </motion.div>

        <h2 className="text-4xl md:text-5xl font-bold mb-3 text-white">
          Starting at <span className="text-yellow-500">${BASE_PRICE.toLocaleString()}</span>
        </h2>
        <p className="text-lg text-slate-400 max-w-2xl mx-auto">
          Professional website delivered in {deliveryDays === 1 ? "24 hours" : "3 days"}.
          Customize your package below.
        </p>
      </div>

      <div className="grid lg:grid-cols-3 gap-8 items-start">
        {/* Add-ons Grid */}
        <div className="lg:col-span-2 space-y-3">
          {/* Base included */}
          <div className="p-5 rounded-2xl bg-yellow-500/10 border border-yellow-500/30">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="w-11 h-11 rounded-xl bg-yellow-500/20 flex items-center justify-center">
                  <Zap className="w-5 h-5 text-yellow-500" />
                </div>
                <div>
                  <div className="font-semibold text-white text-lg">Professional Website</div>
                  <div className="text-sm text-slate-400">
                    Custom landing page, responsive, SEO basics, 1-year hosting
                  </div>
                </div>
              </div>
              <div className="text-right">
                <div className="font-bold text-yellow-500 text-xl">${BASE_PRICE.toLocaleString()}</div>
                <div className="text-xs text-slate-500">included</div>
              </div>
            </div>
          </div>

          {/* Add-on items */}
          {ADD_ONS.map((addon) => {
            const Icon = ADDON_ICONS[addon.id] || Zap;
            const isSelected = (selectedAddOns[addon.id] || 0) > 0;
            const qty = selectedAddOns[addon.id] || 0;

            return (
              <motion.div
                key={addon.id}
                whileHover={{ scale: 1.01 }}
                whileTap={{ scale: 0.99 }}
                onClick={() => {
                  if (addon.type === "toggle") toggleAddon(addon);
                }}
                className={`p-5 rounded-2xl border transition-all cursor-pointer ${
                  isSelected
                    ? "bg-white/10 border-yellow-500/50 shadow-lg shadow-yellow-500/5"
                    : "bg-white/5 border-white/10 hover:border-white/20"
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div
                      className={`w-11 h-11 rounded-xl flex items-center justify-center transition-colors ${
                        isSelected ? "bg-yellow-500/20" : "bg-white/5"
                      }`}
                    >
                      <Icon
                        className={`w-5 h-5 ${
                          isSelected ? "text-yellow-500" : "text-slate-400"
                        }`}
                      />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-white">{addon.name}</span>
                        {addon.popular && (
                          <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded-full bg-yellow-500/20 text-yellow-500">
                            Popular
                          </span>
                        )}
                      </div>
                      <div className="text-sm text-slate-400">{addon.description}</div>
                    </div>
                  </div>

                  <div className="flex items-center gap-4">
                    {addon.type === "quantity" && (
                      <div
                        className="flex items-center gap-2"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <button
                          onClick={() => setQuantity(addon.id, qty - 1)}
                          disabled={qty <= 0}
                          className="w-8 h-8 rounded-lg bg-white/10 flex items-center justify-center text-white hover:bg-white/20 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                        >
                          <Minus className="w-4 h-4" />
                        </button>
                        <span className="w-6 text-center font-semibold text-white">{qty}</span>
                        <button
                          onClick={() => setQuantity(addon.id, qty + 1)}
                          disabled={qty >= (addon.maxQuantity || 10)}
                          className="w-8 h-8 rounded-lg bg-white/10 flex items-center justify-center text-white hover:bg-white/20 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                        >
                          <Plus className="w-4 h-4" />
                        </button>
                      </div>
                    )}

                    <div className="text-right min-w-[70px]">
                      <div className="font-bold text-white">
                        +${addon.price}
                        {addon.type === "quantity" && (
                          <span className="text-slate-400 font-normal text-sm">/ea</span>
                        )}
                      </div>
                    </div>

                    {addon.type === "toggle" && (
                      <div
                        className={`w-6 h-6 rounded-full border-2 flex items-center justify-center transition-all ${
                          isSelected
                            ? "bg-yellow-500 border-yellow-500"
                            : "border-slate-500"
                        }`}
                      >
                        {isSelected && <CheckCircle2 className="w-4 h-4 text-slate-900" />}
                      </div>
                    )}
                  </div>
                </div>
              </motion.div>
            );
          })}
        </div>

        {/* Summary Card - Sticky */}
        <div className="lg:sticky lg:top-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            viewport={{ once: true }}
            className="p-8 rounded-3xl bg-gradient-to-br from-slate-800/80 to-slate-900/80 border border-white/10 backdrop-blur-xl"
          >
            <h3 className="text-lg font-semibold text-white mb-6">Your Package</h3>

            {/* Line items */}
            <div className="space-y-3 mb-6">
              <div className="flex justify-between text-sm">
                <span className="text-slate-300">Professional Website</span>
                <span className="text-white font-medium">${BASE_PRICE.toLocaleString()}</span>
              </div>

              <AnimatePresence>
                {ADD_ONS.filter((a) => (selectedAddOns[a.id] || 0) > 0).map((addon) => {
                  const qty = selectedAddOns[addon.id] || 0;
                  return (
                    <motion.div
                      key={addon.id}
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      exit={{ opacity: 0, height: 0 }}
                      className="flex justify-between text-sm"
                    >
                      <span className="text-slate-300">
                        {addon.name}
                        {qty > 1 && ` x${qty}`}
                      </span>
                      <span className="text-white font-medium">
                        +${(addon.price * qty).toLocaleString()}
                      </span>
                    </motion.div>
                  );
                })}
              </AnimatePresence>
            </div>

            {/* Divider */}
            <div className="h-px bg-white/10 mb-6" />

            {/* Total */}
            <div className="flex justify-between items-end mb-2">
              <span className="text-slate-400 text-sm">Total</span>
              <motion.span
                key={total}
                initial={{ scale: 1.1 }}
                animate={{ scale: 1 }}
                className="text-3xl font-bold text-white"
              >
                ${total.toLocaleString()}
              </motion.span>
            </div>
            <div className="text-right text-xs text-slate-500 mb-6">one-time payment</div>

            {/* Delivery info */}
            <div className="flex items-center gap-3 p-3 rounded-xl bg-white/5 mb-6">
              <Clock className="w-5 h-5 text-yellow-500 flex-shrink-0" />
              <div>
                <div className="text-sm font-medium text-white">
                  {deliveryDays === 1 ? "Priority: 24h delivery" : "Delivered in 3 days"}
                </div>
                <div className="text-xs text-slate-400">
                  {totalPages} page{totalPages > 1 ? "s" : ""} included
                </div>
              </div>
            </div>

            {/* CTA */}
            <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
              <Button
                onClick={() => onCheckout(selectedAddOns)}
                disabled={isLoading}
                className="w-full py-6 text-lg font-bold bg-yellow-500 hover:bg-yellow-600 text-slate-900 rounded-xl shadow-2xl shadow-yellow-500/50 transition-all disabled:opacity-50"
              >
                {isLoading ? (
                  "Processing..."
                ) : (
                  <>
                    <Zap className="mr-2 w-5 h-5" />
                    Continue to Payment
                  </>
                )}
              </Button>
            </motion.div>

            <p className="text-center text-xs text-slate-500 mt-4">
              Secure payment via Stripe
            </p>

            {/* Guarantees */}
            <div className="mt-6 space-y-2">
              {["Money-back guarantee", "No hidden fees", "Direct support included"].map(
                (item) => (
                  <div key={item} className="flex items-center gap-2">
                    <CheckCircle2 className="w-3.5 h-3.5 text-green-500 flex-shrink-0" />
                    <span className="text-xs text-slate-400">{item}</span>
                  </div>
                )
              )}
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
}
