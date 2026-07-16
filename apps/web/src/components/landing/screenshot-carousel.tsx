"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronLeft, ChevronRight } from "lucide-react";

const SCREENSHOTS = [
  "/screenshots/award-site-1.svg",
  "/screenshots/award-site-2.svg",
  "/screenshots/award-site-3.svg",
  "/screenshots/award-site-4.svg",
  "/screenshots/award-site-5.svg",
  "/screenshots/award-site-6.svg",
];

export function ScreenshotCarousel() {
  const [current, setCurrent] = useState(0);
  const [isAutoPlay, setIsAutoPlay] = useState(true);

  useEffect(() => {
    if (!isAutoPlay) return;

    const timer = setInterval(() => {
      setCurrent((prev) => (prev + 1) % SCREENSHOTS.length);
    }, 5000);

    return () => clearInterval(timer);
  }, [isAutoPlay]);

  const next = () => {
    setCurrent((prev) => (prev + 1) % SCREENSHOTS.length);
    setIsAutoPlay(false);
  };

  const prev = () => {
    setCurrent((prev) => (prev - 1 + SCREENSHOTS.length) % SCREENSHOTS.length);
    setIsAutoPlay(false);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 40 }}
      whileInView={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.3, duration: 0.8 }}
      viewport={{ once: true }}
      className="mt-24"
    >
      <div className="max-w-5xl mx-auto px-6">
        <div className="text-center mb-12">
          <p className="text-sm text-yellow-500 font-semibold mb-2">
            Real Examples
          </p>
          <h3 className="text-3xl md:text-4xl font-bold text-white">
            Examples from <span className="text-yellow-500">award-winning websites</span>
          </h3>
        </div>

        <div
          className="relative rounded-2xl overflow-hidden bg-slate-900/50 backdrop-blur-sm border border-white/10"
          onMouseEnter={() => setIsAutoPlay(false)}
          onMouseLeave={() => setIsAutoPlay(true)}
        >
          <div className="relative aspect-video bg-slate-950">
            <AnimatePresence mode="wait">
              <motion.div
                key={current}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.5 }}
                className="absolute inset-0"
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={SCREENSHOTS[current]}
                  alt={`Award-winning website example ${current + 1}`}
                  className="w-full h-full object-cover"
                  onError={(e) => {
                    e.currentTarget.src = "/grid.svg";
                  }}
                />
              </motion.div>
            </AnimatePresence>

            {/* Navigation Buttons */}
            <button
              onClick={prev}
              className="absolute left-4 top-1/2 -translate-y-1/2 z-20 p-2 rounded-full bg-black/50 hover:bg-black/70 text-white transition-colors backdrop-blur-sm"
              aria-label="Previous slide"
            >
              <ChevronLeft size={24} />
            </button>
            <button
              onClick={next}
              className="absolute right-4 top-1/2 -translate-y-1/2 z-20 p-2 rounded-full bg-black/50 hover:bg-black/70 text-white transition-colors backdrop-blur-sm"
              aria-label="Next slide"
            >
              <ChevronRight size={24} />
            </button>

            {/* Indicators */}
            <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex gap-2 z-20">
              {SCREENSHOTS.map((_, i) => (
                <button
                  key={i}
                  onClick={() => {
                    setCurrent(i);
                    setIsAutoPlay(false);
                  }}
                  className={`h-2 rounded-full transition-all ${
                    i === current
                      ? "bg-yellow-500 w-8"
                      : "bg-white/30 w-2 hover:bg-white/50"
                  }`}
                  aria-label={`Go to slide ${i + 1}`}
                />
              ))}
            </div>
          </div>
        </div>

        {/* Caption */}
        <p className="text-center text-slate-400 mt-6 text-sm">
          Slide {current + 1} of {SCREENSHOTS.length}
        </p>
      </div>
    </motion.div>
  );
}
