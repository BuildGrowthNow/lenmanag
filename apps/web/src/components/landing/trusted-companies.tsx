"use client";

import { motion } from "framer-motion";
import Image from "next/image";
import { useSupportsHover } from "@/hooks/use-supports-hover";

const COMPANIES = [
  { name: "Banco Santander", logo: "/logos/Banco_Santander.svg" },
  { name: "Disney+", logo: "/logos/Disney.svg" },
  { name: "MongoDB", logo: "/logos/MongoDB.svg" },
  { name: "YouCan", logo: "/logos/youcan.png" },
  { name: "Looping Livre", logo: "/logos/loopinglivre.png" },
  { name: "Star+", logo: "/logos/Star+.svg" },
  { name: "Nexora", logo: "/logos/nexora.png" },
  { name: "Veltrix", logo: "/logos/veltrix.png" },
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
              viewport={{ once: true, amount: 0.3 }}
              {...(supportsHover && { whileHover: { scale: 1.05 } })}
              className="relative h-8 w-28 cursor-pointer opacity-70 [@media(hover:hover)]:hover:opacity-100 transition-opacity"
            >
              <Image
                src={company.logo}
                alt={company.name}
                fill
                className="object-contain"
              />
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
