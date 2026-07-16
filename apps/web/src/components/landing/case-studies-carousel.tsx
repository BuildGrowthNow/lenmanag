"use client";

import { motion, useMotionValue, useTransform } from "framer-motion";
import { useState, useRef } from "react";
import { ChevronLeft, ChevronRight, MoveHorizontal } from "lucide-react";

const CASE_STUDIES = [
  {
    id: 1,
    clientName: "TechFlow Solutions",
    industry: "Software Company",
    metric1: "Getting 3x more leads every month",
    metric2: "Website loads super fast now",
    metric3: "$45K earned since launch",
    quote: "We went from struggling to explain our product online... to having clients line up. Mind-blowing.",
    beforeImage: "bg-gradient-to-br from-zinc-700 to-zinc-800",
    afterImage: "bg-gradient-to-br from-blue-500 to-cyan-500",
    beforePoints: [
      "❌ Confusing Navigation",
      "❌ No Clear Value Prop",
      "❌ High Bounce Rate",
    ],
    afterPoints: [
      "✅ Intuitive Flow",
      "✅ Clear Messaging",
      "✅ 3x Conversions",
    ],
  },
  {
    id: 2,
    clientName: "EcoGreen Marketing",
    industry: "Marketing Agency",
    metric1: "5x more inquiries coming in",
    metric2: "Way more people staying on the site",
    metric3: "$120K in new client deals",
    quote: "Best money we spent all year. Our phone doesn't stop ringing. This is incredible.",
    beforeImage: "bg-gradient-to-br from-zinc-700 to-zinc-800",
    afterImage: "bg-gradient-to-br from-green-500 to-emerald-500",
    beforePoints: [
      "❌ Generic Template",
      "❌ Slow Load Times",
      "❌ Poor SEO Ranking",
    ],
    afterPoints: [
      "✅ Custom Design",
      "✅ Lightning Fast",
      "✅ Page 1 Google",
    ],
  },
  {
    id: 3,
    clientName: "Coastal Realty Group",
    industry: "Real Estate",
    metric1: "People actually looking at our listings",
    metric2: "Site works perfectly on phones now",
    metric3: "$200K+ in new property sales",
    quote: "Our agents are selling more than ever. They love showing clients the website. Game changer.",
    beforeImage: "bg-gradient-to-br from-zinc-700 to-zinc-800",
    afterImage: "bg-gradient-to-br from-orange-500 to-red-500",
    beforePoints: [
      "❌ Desktop Only",
      "❌ Hard to Find Listings",
      "❌ No Lead Capture",
    ],
    afterPoints: [
      "✅ Mobile First",
      "✅ Smart Search",
      "✅ Auto Lead Forms",
    ],
  },
  {
    id: 4,
    clientName: "Digital Ventures Co",
    industry: "Startup",
    metric1: "Went from zero visibility to everywhere",
    metric2: "People actually stay and explore",
    metric3: "Seriously attracting investor attention",
    quote: "This website is our secret weapon. Investors are impressed. We're finally being taken seriously.",
    beforeImage: "bg-gradient-to-br from-zinc-700 to-zinc-800",
    afterImage: "bg-gradient-to-br from-purple-500 to-pink-500",
    beforePoints: [
      "❌ Looked Amateur",
      "❌ No Social Proof",
      "❌ Low Credibility",
    ],
    afterPoints: [
      "✅ Premium Brand",
      "✅ Trust Signals",
      "✅ Investor Ready",
    ],
  },
];

function BeforeAfterSlider({ study }: { study: typeof CASE_STUDIES[0] }) {
  const [sliderPosition, setSliderPosition] = useState(50);
  const [isDragging, setIsDragging] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const x = useMotionValue(50);
  const clipPath = useTransform(x, (value) => `inset(0 ${100 - value}% 0 0)`);

  const handleMove = (clientX: number) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const position = ((clientX - rect.left) / rect.width) * 100;
    const bounded = Math.max(0, Math.min(100, position));
    setSliderPosition(bounded);
    x.set(bounded);
  };

  const handleMouseDown = () => setIsDragging(true);
  const handleMouseUp = () => setIsDragging(false);

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDragging) handleMove(e.clientX);
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    if (e.touches.length > 0) handleMove(e.touches[0].clientX);
  };

  return (
    <div
      ref={containerRef}
      className="relative aspect-video rounded-2xl overflow-hidden border-2 border-white/10 cursor-ew-resize select-none"
      onMouseDown={handleMouseDown}
      onMouseUp={handleMouseUp}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseUp}
      onTouchStart={handleMouseDown}
      onTouchEnd={handleMouseUp}
      onTouchMove={handleTouchMove}
    >
      {/* Before Image (Background) */}
      <div className={`absolute inset-0 ${study.beforeImage} flex items-center justify-center`}>
        <div className="text-center space-y-2">
          {study.beforePoints.map((point, i) => (
            <div key={i} className="text-zinc-400 text-sm">{point}</div>
          ))}
        </div>
      </div>

      {/* After Image (Overlay) */}
      <motion.div
        className={`absolute inset-0 ${study.afterImage} flex items-center justify-center`}
        style={{ clipPath }}
      >
        <div className="text-center space-y-2">
          {study.afterPoints.map((point, i) => (
            <div key={i} className="text-white text-sm font-semibold">{point}</div>
          ))}
        </div>
      </motion.div>

      {/* Slider Handle */}
      <motion.div
        className="absolute top-0 bottom-0 w-1 bg-white shadow-2xl"
        style={{ left: `${sliderPosition}%`, transform: "translateX(-50%)" }}
      >
        {/* Before Label (Left of line) */}
        <div className="absolute bottom-4 right-3 px-3 py-1 rounded-md bg-zinc-800/90 backdrop-blur-sm border border-white/20">
          <span className="text-xs font-semibold text-zinc-300 uppercase tracking-wider">Before</span>
        </div>

        {/* After Label (Right of line) */}
        <div className="absolute bottom-4 left-3 px-3 py-1 rounded-md bg-gradient-to-r from-yellow-500/90 to-yellow-600/90 backdrop-blur-sm border border-yellow-400/50">
          <span className="text-xs font-bold text-zinc-900 uppercase tracking-wider">After</span>
        </div>
      </motion.div>

      {/* Drag Hint (shows on first render) */}
      {!isDragging && sliderPosition === 50 && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5, duration: 0.5 }}
          className="absolute bottom-4 left-1/2 -translate-x-1/2 px-4 py-2 rounded-full bg-black/70 backdrop-blur-sm text-white text-sm font-medium pointer-events-none"
        >
          👆 Drag to compare
        </motion.div>
      )}
    </div>
  );
}

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
          {/* Before/After Slider */}
          <div className="flex flex-col gap-6">
            <BeforeAfterSlider study={study} />
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
