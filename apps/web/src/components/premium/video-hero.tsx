"use client";

import { motion } from "framer-motion";
import { ReactNode } from "react";

interface VideoHeroProps {
  videoUrl: string;
  posterUrl?: string;
  overlay?: boolean;
  overlayOpacity?: number;
  children: ReactNode;
  className?: string;
}

export function VideoHero({
  videoUrl,
  posterUrl,
  overlay = true,
  overlayOpacity = 0.5,
  children,
  className = "",
}: VideoHeroProps) {
  return (
    <div className={`relative min-h-screen overflow-hidden ${className}`}>
      <video
        autoPlay
        loop
        muted
        playsInline
        poster={posterUrl}
        className="absolute inset-0 h-full w-full object-cover"
      >
        <source src={videoUrl} type="video/mp4" />
      </video>

      {overlay && (
        <div
          className="absolute inset-0 bg-black"
          style={{ opacity: overlayOpacity }}
        />
      )}

      <div className="relative z-10 flex min-h-screen items-center justify-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.3 }}
        >
          {children}
        </motion.div>
      </div>
    </div>
  );
}

interface FullscreenVideoHeroProps {
  videoUrl: string;
  posterUrl?: string;
  headline: string;
  subheadline?: string;
  cta?: ReactNode;
}

export function FullscreenVideoHero({
  videoUrl,
  posterUrl,
  headline,
  subheadline,
  cta,
}: FullscreenVideoHeroProps) {
  return (
    <VideoHero videoUrl={videoUrl} posterUrl={posterUrl}>
      <div className="container mx-auto px-4 text-center text-white">
        <motion.h1
          className="mb-6 text-5xl font-bold leading-tight md:text-7xl"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.5 }}
        >
          {headline}
        </motion.h1>
        {subheadline && (
          <motion.p
            className="mb-8 text-xl md:text-2xl"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.7 }}
          >
            {subheadline}
          </motion.p>
        )}
        {cta && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.9 }}
          >
            {cta}
          </motion.div>
        )}
      </div>
    </VideoHero>
  );
}
