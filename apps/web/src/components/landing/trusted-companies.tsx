"use client";

import { motion } from "framer-motion";
import Image from "next/image";
import { useSupportsHover } from "@/hooks/use-supports-hover";

const COMPANIES = [
  { name: "Nexora", logo: "/logos/nexora.png" },
  { name: "Veltrix", logo: "/logos/veltrix.png" },
  { name: "CloudByte", logo: "/logos/cloudbyte.png" },
  { name: "Pulse.io", logo: "/logos/pulseio.png" },
  { name: "Synthwave", logo: "/logos/synthwave.png" },
  { name: "DataCore", logo: "/logos/datacore.png" },
];

export function TrustedCompanies() {
  const supportsHover = useSupportsHover();

  return (
    <section className="relative px-6 py-8">
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

        <div className="flex flex-wrap items-center justify-center gap-x-10 gap-y-6">
          {COMPANIES.map((company, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, scale: 0.8 }}
              whileInView={{ opacity: 1, scale: 1 }}
              transition={{ delay: i * 0.05, duration: 0.4 }}
              viewport={{ once: true }}
              {...(supportsHover && { whileHover: { scale: 1.05 } })}
              className="flex items-center gap-2 group cursor-pointer"
            >
              <Image
                src={company.logo}
                alt={company.name}
                width={32}
                height={32}
                className="transition-transform group-hover:scale-110"
              />
              <span className="text-slate-300 font-medium group-hover:text-yellow-500 transition-colors text-sm">
                {company.name}
              </span>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
