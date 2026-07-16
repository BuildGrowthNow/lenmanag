"use client";

import { motion } from "framer-motion";

function TechVentureIcon() {
  return (
    <svg viewBox="0 0 32 32" className="w-8 h-8">
      <defs>
        <linearGradient id="techGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#f59e0b" />
          <stop offset="100%" stopColor="#fbbf24" />
        </linearGradient>
      </defs>
      <rect x="1" y="1" width="30" height="30" fill="none" stroke="url(#techGrad)" strokeWidth="2" rx="6"/>
      <path d="M8 13 L16 6 L24 13" fill="none" stroke="#fbbf24" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
      <circle cx="16" cy="18" r="4" fill="#f59e0b"/>
      <circle cx="16" cy="18" r="2" fill="#fbbf24"/>
    </svg>
  );
}

function CloudFirstIcon() {
  return (
    <svg viewBox="0 0 32 32" className="w-8 h-8">
      <defs>
        <linearGradient id="cloudGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#06b6d4" />
          <stop offset="100%" stopColor="#0891b2" />
        </linearGradient>
      </defs>
      <path d="M6 16 Q6 10 12 10 Q13.5 5 18 5 Q24 5 24 11 Q28 11 28 16 Q28 20 24 22 L10 22 Q6 22 6 18 Z" fill="url(#cloudGrad)" opacity="0.2"/>
      <path d="M6 16 Q6 10 12 10 Q13.5 5 18 5 Q24 5 24 11 Q28 11 28 16 Q28 20 24 22 L10 22 Q6 22 6 18 Z" fill="none" stroke="#06b6d4" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <line x1="11" y1="17" x2="11" y2="22" stroke="#0891b2" strokeWidth="2" strokeLinecap="round"/>
      <line x1="16" y1="17" x2="16" y2="22" stroke="#0891b2" strokeWidth="2" strokeLinecap="round"/>
      <line x1="21" y1="17" x2="21" y2="22" stroke="#0891b2" strokeWidth="2" strokeLinecap="round"/>
    </svg>
  );
}

function DataFlowIcon() {
  return (
    <svg viewBox="0 0 32 32" className="w-8 h-8">
      <defs>
        <linearGradient id="dataGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#8b5cf6" />
          <stop offset="100%" stopColor="#a78bfa" />
        </linearGradient>
      </defs>
      <circle cx="8" cy="8" r="3" fill="url(#dataGrad)"/>
      <circle cx="24" cy="8" r="3" fill="url(#dataGrad)"/>
      <circle cx="8" cy="24" r="3" fill="url(#dataGrad)"/>
      <circle cx="24" cy="24" r="3" fill="url(#dataGrad)"/>
      <circle cx="16" cy="16" r="5" fill="#a78bfa"/>
      <circle cx="16" cy="16" r="3" fill="#8b5cf6"/>
      <path d="M10 10 L13 13" stroke="#8b5cf6" strokeWidth="2" strokeLinecap="round"/>
      <path d="M22 10 L19 13" stroke="#8b5cf6" strokeWidth="2" strokeLinecap="round"/>
      <path d="M10 22 L13 19" stroke="#8b5cf6" strokeWidth="2" strokeLinecap="round"/>
      <path d="M22 22 L19 19" stroke="#8b5cf6" strokeWidth="2" strokeLinecap="round"/>
    </svg>
  );
}

function GrowthLabsIcon() {
  return (
    <svg viewBox="0 0 32 32" className="w-8 h-8">
      <defs>
        <linearGradient id="growthGrad" x1="0%" y1="100%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#059669" />
          <stop offset="100%" stopColor="#10b981" />
        </linearGradient>
      </defs>
      <path d="M4 24 L10 15 L15 19 L28 6" fill="none" stroke="url(#growthGrad)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
      <circle cx="4" cy="24" r="2.5" fill="#10b981"/>
      <circle cx="10" cy="15" r="2.5" fill="#10b981"/>
      <circle cx="15" cy="19" r="2.5" fill="#10b981"/>
      <circle cx="28" cy="6" r="2.5" fill="#10b981"/>
      <path d="M23 6 L28 6 L28 11" fill="none" stroke="#10b981" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );
}

function InnovateProIcon() {
  return (
    <svg viewBox="0 0 32 32" className="w-8 h-8">
      <defs>
        <linearGradient id="innovateGrad" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="#fbbf24" />
          <stop offset="100%" stopColor="#f59e0b" />
        </linearGradient>
      </defs>
      <circle cx="16" cy="12" r="6" fill="url(#innovateGrad)" opacity="0.2"/>
      <circle cx="16" cy="12" r="6" fill="none" stroke="#fbbf24" strokeWidth="2"/>
      <circle cx="16" cy="12" r="3" fill="#fbbf24"/>
      <ellipse cx="16" cy="22" rx="8" ry="6" fill="none" stroke="#f59e0b" strokeWidth="2"/>
      <path d="M12 24 L10 30 M20 24 L22 30 M16 28 L16 32" stroke="#f59e0b" strokeWidth="2" strokeLinecap="round"/>
    </svg>
  );
}

function ScaleHubIcon() {
  return (
    <svg viewBox="0 0 32 32" className="w-8 h-8">
      <defs>
        <linearGradient id="scaleGrad" x1="0%" y1="100%" x2="0%" y2="0%">
          <stop offset="0%" stopColor="#0891b2" />
          <stop offset="100%" stopColor="#06b6d4" />
        </linearGradient>
      </defs>
      <rect x="4" y="16" width="6" height="12" fill="url(#scaleGrad)" rx="1"/>
      <rect x="13" y="10" width="6" height="18" fill="url(#scaleGrad)" rx="1"/>
      <rect x="22" y="4" width="6" height="24" fill="url(#scaleGrad)" rx="1"/>
      <circle cx="7" cy="28" r="1.5" fill="#06b6d4"/>
      <circle cx="16" cy="28" r="1.5" fill="#06b6d4"/>
      <circle cx="25" cy="28" r="1.5" fill="#06b6d4"/>
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
    <section className="relative px-6 py-8 bg-zinc-900/30">
      <div className="max-w-7xl mx-auto">
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          transition={{ duration: 0.8 }}
          viewport={{ once: true }}
          className="text-center mb-8"
        >
          <p className="text-slate-400 text-sm uppercase tracking-wider">
            Trusted by Forward-Thinking Companies
          </p>
        </motion.div>

        <div className="flex flex-wrap items-center justify-center gap-x-8 gap-y-4">
          {COMPANIES.map((company, i) => {
            const Icon = company.icon;
            return (
              <motion.div
                key={i}
                initial={{ opacity: 0, scale: 0.8 }}
                whileInView={{ opacity: 1, scale: 1 }}
                transition={{ delay: i * 0.05, duration: 0.4 }}
                viewport={{ once: true }}
                whileHover={{ scale: 1.05 }}
                className="flex items-center gap-3 group cursor-pointer"
              >
                <div className="transition-transform group-hover:scale-110">
                  <Icon />
                </div>
                <span className="text-slate-300 font-medium group-hover:text-yellow-500 transition-colors">
                  {company.name}
                </span>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
