"use client";

import { motion } from "framer-motion";

function TechVentureIcon() {
  return (
    <svg viewBox="0 0 40 40" className="w-10 h-10">
      <rect x="2" y="2" width="36" height="36" fill="none" stroke="#f59e0b" strokeWidth="1.5" rx="4"/>
      <path d="M10 15 L20 5 L30 15" fill="none" stroke="#fbbf24" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <circle cx="20" cy="22" r="4" fill="#f59e0b"/>
    </svg>
  );
}

function CloudFirstIcon() {
  return (
    <svg viewBox="0 0 40 40" className="w-10 h-10">
      <path d="M8 20 Q8 12 16 12 Q18 6 24 6 Q32 6 32 14 Q32 14 32 14 Q38 14 38 20 Q38 25 32 28 L12 28 Q8 28 8 24 Z" fill="none" stroke="#06b6d4" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
      <line x1="14" y1="22" x2="14" y2="28" stroke="#0891b2" strokeWidth="1.5" strokeLinecap="round"/>
      <line x1="20" y1="22" x2="20" y2="28" stroke="#0891b2" strokeWidth="1.5" strokeLinecap="round"/>
      <line x1="26" y1="22" x2="26" y2="28" stroke="#0891b2" strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  );
}

function DataFlowIcon() {
  return (
    <svg viewBox="0 0 40 40" className="w-10 h-10">
      <circle cx="10" cy="10" r="3" fill="#8b5cf6"/>
      <circle cx="30" cy="10" r="3" fill="#8b5cf6"/>
      <circle cx="10" cy="30" r="3" fill="#8b5cf6"/>
      <circle cx="30" cy="30" r="3" fill="#8b5cf6"/>
      <circle cx="20" cy="20" r="4" fill="#a78bfa"/>
      <path d="M13 12 L17 18" stroke="#8b5cf6" strokeWidth="1.5" fill="none"/>
      <path d="M27 12 L23 18" stroke="#8b5cf6" strokeWidth="1.5" fill="none"/>
      <path d="M13 28 L17 22" stroke="#8b5cf6" strokeWidth="1.5" fill="none"/>
      <path d="M27 28 L23 22" stroke="#8b5cf6" strokeWidth="1.5" fill="none"/>
    </svg>
  );
}

function GrowthLabsIcon() {
  return (
    <svg viewBox="0 0 40 40" className="w-10 h-10">
      <path d="M8 28 L15 18 L20 22 L32 8" fill="none" stroke="#10b981" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <circle cx="8" cy="28" r="2" fill="#10b981"/>
      <circle cx="15" cy="18" r="2" fill="#10b981"/>
      <circle cx="20" cy="22" r="2" fill="#10b981"/>
      <circle cx="32" cy="8" r="2" fill="#10b981"/>
      <line x1="32" y1="8" x2="35" y2="5" stroke="#10b981" strokeWidth="2" strokeLinecap="round"/>
      <line x1="32" y1="8" x2="35" y2="8" stroke="#10b981" strokeWidth="2" strokeLinecap="round"/>
    </svg>
  );
}

function InnovateProIcon() {
  return (
    <svg viewBox="0 0 40 40" className="w-10 h-10">
      <circle cx="20" cy="24" r="10" fill="none" stroke="#f59e0b" strokeWidth="1.5"/>
      <circle cx="20" cy="12" r="5" fill="none" stroke="#fbbf24" strokeWidth="2"/>
      <path d="M16 28 L14 34 M24 28 L26 34 M20 34 L20 38" stroke="#f59e0b" strokeWidth="1.5" strokeLinecap="round"/>
      <circle cx="20" cy="12" r="2" fill="#fbbf24"/>
    </svg>
  );
}

function ScaleHubIcon() {
  return (
    <svg viewBox="0 0 40 40" className="w-10 h-10">
      <rect x="6" y="14" width="8" height="18" fill="none" stroke="#06b6d4" strokeWidth="1.5" rx="1"/>
      <rect x="16" y="8" width="8" height="24" fill="none" stroke="#0891b2" strokeWidth="1.5" rx="1"/>
      <rect x="26" y="2" width="8" height="30" fill="none" stroke="#06b6d4" strokeWidth="1.5" rx="1"/>
      <circle cx="10" cy="32" r="1.5" fill="#06b6d4"/>
      <circle cx="20" cy="32" r="1.5" fill="#06b6d4"/>
      <circle cx="30" cy="32" r="1.5" fill="#06b6d4"/>
    </svg>
  );
}

const COMPANIES = [
  { name: "TechVenture Co", icon: TechVentureIcon },
  { name: "CloudFirst Inc", icon: CloudFirstIcon },
  { name: "DataFlow Systems", icon: DataFlowIcon },
  { name: "GrowthLabs", icon: GrowthLabsIcon },
  { name: "InnovatePro", icon: InnovateProIcon },
  { name: "ScaleHub", icon: ScaleHubIcon },
];

export function TrustedCompanies() {
  return (
    <section className="relative px-6 py-16 bg-zinc-900/30">
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

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {COMPANIES.map((company, i) => {
            const Icon = company.icon;
            return (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.1, duration: 0.5 }}
                viewport={{ once: true }}
                whileHover={{ scale: 1.05, y: -5 }}
                className="flex flex-col items-center justify-center p-8 rounded-2xl bg-white/5 backdrop-blur-sm border border-white/10 hover:border-yellow-500/30 transition-all group relative overflow-hidden"
              >
                <motion.div
                  className="absolute inset-0 rounded-2xl bg-gradient-to-r from-yellow-500/0 via-yellow-500/10 to-yellow-500/0 pointer-events-none"
                  animate={{
                    opacity: [0.3, 0.6, 0.3],
                  }}
                  transition={{
                    duration: 3,
                    repeat: Infinity,
                    delay: i * 0.2,
                  }}
                />
                <div className="relative z-10">
                  <div className="mb-4 p-4 rounded-xl bg-white/5 group-hover:bg-yellow-500/10 transition-colors">
                    <Icon />
                  </div>
                  <div className="text-center">
                    <div className="text-lg font-bold text-white group-hover:text-yellow-500 transition-colors">
                      {company.name}
                    </div>
                  </div>
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
