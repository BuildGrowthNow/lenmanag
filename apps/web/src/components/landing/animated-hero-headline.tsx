"use client";

import { motion } from "framer-motion";
import { useEffect, useState } from "react";

const PHRASES_DESKTOP = ["In 3 Days", "$1,000", "with a Master Design"];
const PHRASES_MOBILE = ["In 3 Days", "$1,000", "Best Design"];

export function AnimatedHeroHeadline() {
  const [currentPhraseIndex, setCurrentPhraseIndex] = useState(0);
  const [displayedText, setDisplayedText] = useState("");
  const [isDeleting, setIsDeleting] = useState(false);
  const [showCursor, setShowCursor] = useState(true);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(max-width: 767px)");
    setIsMobile(mq.matches);
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  useEffect(() => {
    const PHRASES = isMobile ? PHRASES_MOBILE : PHRASES_DESKTOP;
    const currentPhrase = PHRASES[currentPhraseIndex];

    if (!isDeleting && displayedText === currentPhrase) {
      const pauseTimer = setTimeout(() => {
        setIsDeleting(true);
      }, 2000);
      return () => clearTimeout(pauseTimer);
    }

    if (isDeleting && displayedText === "") {
      setIsDeleting(false);
      setCurrentPhraseIndex((prev) => (prev + 1) % PHRASES.length);
      return;
    }

    const typingSpeed = isDeleting ? 50 : 100;
    const timer = setTimeout(() => {
      setDisplayedText(
        isDeleting
          ? currentPhrase.substring(0, displayedText.length - 1)
          : currentPhrase.substring(0, displayedText.length + 1)
      );
    }, typingSpeed);

    return () => clearTimeout(timer);
  }, [displayedText, isDeleting, currentPhraseIndex, isMobile]);

  useEffect(() => {
    const cursorTimer = setInterval(() => {
      setShowCursor((prev) => !prev);
    }, 500);
    return () => clearInterval(cursorTimer);
  }, []);

  return (
    <div className="text-center">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        >
        <h1 className="text-5xl md:text-7xl font-bold text-white">
          Your Website
        </h1>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.2 }}
        className="mb-3 flex items-center justify-center"
      >
        <h2 className="text-5xl md:text-7xl font-bold leading-normal bg-gradient-to-r from-yellow-400 via-yellow-300 to-yellow-500 bg-clip-text text-transparent">
          {displayedText}
          <span
            className={`inline-block w-1 h-[1em] ml-1 bg-yellow-500 ${
              showCursor ? "opacity-100" : "opacity-0"
            }`}
          />
        </h2>
      </motion.div>

      <motion.p
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.4 }}
        className="text-xl md:text-2xl text-slate-300 max-w-3xl mx-auto"
      >
        Premium, custom-crafted websites built by design experts.
        <br className="hidden md:block" />
        <span className="text-yellow-500 font-semibold">
          &nbsp;No compromises. No delays. Just masterfully executed results.
        </span>
      </motion.p>
    </div>
  );
}
