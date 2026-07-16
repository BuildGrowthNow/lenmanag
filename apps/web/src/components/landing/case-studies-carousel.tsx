"use client";

import { motion } from "framer-motion";
import { useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";

const CASE_STUDIES = [
  {
    id: 1,
    clientName: "TechFlow Solutions",
    industry: "Software Company",
    metric1: "Getting 3x more leads every month",
    metric2: "Website loads super fast now",
    metric3: "$45K earned since launch",
    quote: "We went from struggling to explain our product online... to having clients line up. Mind-blowing.",
    image: "bg-gradient-to-br from-blue-500 to-cyan-500",
  },
  {
    id: 2,
    clientName: "EcoGreen Marketing",
    industry: "Marketing Agency",
    metric1: "5x more inquiries coming in",
    metric2: "Way more people staying on the site",
    metric3: "$120K in new client deals",
    quote: "Best money we spent all year. Our phone doesn't stop ringing. This is incredible.",
    image: "bg-gradient-to-br from-green-500 to-emerald-500",
  },
  {
    id: 3,
    clientName: "Coastal Realty Group",
    industry: "Real Estate",
    metric1: "People actually looking at our listings",
    metric2: "Site works perfectly on phones now",
    metric3: "$200K+ in new property sales",
    quote: "Our agents are selling more than ever. They love showing clients the website. Game changer.",
    image: "bg-gradient-to-br from-orange-500 to-red-500",
  },
  {
    id: 4,
    clientName: "Digital Ventures Co",
    industry: "Startup",
    metric1: "Went from zero visibility to everywhere",
    metric2: "People actually stay and explore",
    metric3: "Seriously attracting investor attention",
    quote: "This website is our secret weapon. Investors are impressed. We're finally being taken seriously.",
    image: "bg-gradient-to-br from-purple-500 to-pink-500",
  },
];

export function CaseStudiesCarousel() {
  const [current, setCurrent] = useState(0);

  const next = () => setCurrent((prev) => (prev + 1) % CASE_STUDIES.length);
  const prev = () =>
    setCurrent((prev) => (prev - 1 + CASE_STUDIES.length) % CASE_STUDIES.length);

  const study = CASE_STUDIES[current];

  return (
    <section className="relative px-6 py-24 bg-gradient-to-b from-zinc-900 to-zinc-950">
      <div className="max-w-6xl mx-auto">
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          transition={{ duration: 0.8 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <h2 className="text-5xl font-bold mb-4 text-white">
            Real Results. Real <span className="text-yellow-500">Clients.</span>
          </h2>
          <p className="text-xl text-zinc-400">
            See how we transformed businesses just like yours
          </p>
        </motion.div>

        {/* Case Study Display */}
        <motion.div
          key={current}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          transition={{ duration: 0.5 }}
          className="grid md:grid-cols-2 gap-8 items-center mb-12"
        >
          {/* Before/After Visual */}
          <div className="flex flex-col gap-6">
            <div className="grid grid-cols-2 gap-4">
              {/* Before */}
              <motion.div
                whileHover={{ scale: 1.05 }}
                className="rounded-xl overflow-hidden border border-white/10"
              >
                <div className="aspect-video bg-gradient-to-br from-zinc-600 to-zinc-700 flex items-center justify-center">
                  <div className="text-center">
                    <div className="text-sm text-zinc-300 mb-2">Before</div>
                    <div className="text-2xl font-bold text-zinc-400">📱</div>
                  </div>
                </div>
              </motion.div>

              {/* After */}
              <motion.div
                whileHover={{ scale: 1.05 }}
                className={`rounded-xl overflow-hidden border-2 border-yellow-500/50 ${study.image}`}
              >
                <div className="aspect-video flex items-center justify-center">
                  <div className="text-center">
                    <div className="text-sm text-white mb-2 font-semibold">After</div>
                    <div className="text-2xl font-bold text-white">✨</div>
                  </div>
                </div>
              </motion.div>
            </div>
          </div>

          {/* Case Study Details */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2 }}
            className="space-y-6"
          >
            <div>
              <h3 className="text-3xl font-bold text-white mb-2">
                {study.clientName}
              </h3>
              <p className="text-sm text-yellow-500 font-semibold uppercase tracking-wider">
                {study.industry}
              </p>
            </div>

                {/* Metrics */}
            <div className="grid grid-cols-1 gap-3 p-6 rounded-xl bg-white/5 border border-white/10">
              <motion.div
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.3 }}
                whileHover={{ x: 5, scale: 1.02 }}
                className="flex items-center gap-3 cursor-pointer"
              >
                <motion.span
                  animate={{ scale: [1, 1.3, 1] }}
                  transition={{ duration: 0.6, delay: 0.3 }}
                  className="text-2xl"
                >
                  📈
                </motion.span>
                <span className="text-white font-semibold">{study.metric1}</span>
              </motion.div>
              <motion.div
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.4 }}
                whileHover={{ x: 5, scale: 1.02 }}
                className="flex items-center gap-3 cursor-pointer"
              >
                <motion.span
                  animate={{ scale: [1, 1.3, 1] }}
                  transition={{ duration: 0.6, delay: 0.4 }}
                  className="text-2xl"
                >
                  ⚡
                </motion.span>
                <span className="text-white font-semibold">{study.metric2}</span>
              </motion.div>
              <motion.div
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.5 }}
                whileHover={{ x: 5, scale: 1.02 }}
                className="flex items-center gap-3 cursor-pointer"
              >
                <motion.span
                  animate={{ scale: [1, 1.3, 1] }}
                  transition={{ duration: 0.6, delay: 0.5 }}
                  className="text-2xl"
                >
                  💰
                </motion.span>
                <span className="text-white font-semibold">{study.metric3}</span>
              </motion.div>
            </div>

            {/* Quote */}
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6 }}
              className="p-4 rounded-lg bg-yellow-500/10 border border-yellow-500/30"
            >
              <p className="text-white italic">&quot;{study.quote}&quot;</p>
              <p className="text-sm text-zinc-400 mt-2">
                — {study.clientName} Team
              </p>
            </motion.div>
          </motion.div>
        </motion.div>

        {/* Navigation */}
        <div className="flex items-center justify-center gap-6">
          <button
            onClick={prev}
            className="p-3 rounded-full bg-white/10 hover:bg-yellow-500/20 text-white transition-all"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>

          <div className="flex gap-2">
            {CASE_STUDIES.map((_, i) => (
              <button
                key={i}
                onClick={() => setCurrent(i)}
                className={`w-2 h-2 rounded-full transition-all ${
                  i === current ? "bg-yellow-500 w-6" : "bg-white/30"
                }`}
              />
            ))}
          </div>

          <button
            onClick={next}
            className="p-3 rounded-full bg-white/10 hover:bg-yellow-500/20 text-white transition-all"
          >
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>

        {/* Counter */}
        <motion.p
          className="text-center mt-8 text-zinc-400"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          Case study {current + 1} of {CASE_STUDIES.length}
        </motion.p>
      </div>
    </section>
  );
}
