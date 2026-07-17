"use client";

import { motion } from "framer-motion";
import { useSupportsHover } from "@/hooks/use-supports-hover";

const COMPANY_LOGOS = [
  { name: "NexaTech", tagline: "Enterprise Solutions" },
  { name: "Velocity", tagline: "Marketing Agency" },
  { name: "Horizon", tagline: "Financial Services" },
  { name: "Innovate", tagline: "Startup Hub" },
  { name: "Zenith", tagline: "Consulting Group" },
  { name: "Quantum", tagline: "Analytics Platform" },
  { name: "Pulse", tagline: "Healthcare Tech" },
  { name: "Summit", tagline: "Real Estate" },
  { name: "Catalyst", tagline: "EdTech Solutions" },
  { name: "Momentum", tagline: "E-commerce" },
  { name: "Elevate", tagline: "B2B Services" },
  { name: "Synergy", tagline: "Logistics" },
];

export function LogoWall() {
  const supportsHover = useSupportsHover();

  return (
    <section className="relative px-6 py-16 bg-slate-900/30">
      <div className="max-w-7xl mx-auto">
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          transition={{ duration: 0.8 }}
          viewport={{ once: true }}
          className="text-center mb-12"
        >
          <p className="text-slate-400 text-sm uppercase tracking-wider mb-8">
            Trusted by forward-thinking companies
          </p>
        </motion.div>

        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-8">
          {COMPANY_LOGOS.map((company, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05, duration: 0.5 }}
              viewport={{ once: true, amount: 0.3 }}
              {...(supportsHover && { whileHover: { scale: 1.05, y: -5 } })}
              className="flex flex-col items-center justify-center p-6 rounded-xl bg-white/5 backdrop-blur-sm border border-white/10 [@media(hover:hover)]:hover:border-yellow-500/30 transition-all group"
            >
              <div className="text-center">
                <div className="text-lg font-bold text-white mb-1 group-hover:text-yellow-500 transition-colors">
                  {company.name}
                </div>
                <div className="text-xs text-slate-500">{company.tagline}</div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
