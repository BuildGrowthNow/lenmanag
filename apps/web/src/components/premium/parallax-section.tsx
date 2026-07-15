"use client";

import { motion, useScroll, useTransform } from "framer-motion";
import { ReactNode, useRef } from "react";

interface ParallaxSectionProps {
  children: ReactNode;
  speed?: number;
  className?: string;
  offset?: number;
}

export function ParallaxSection({
  children,
  speed = 0.5,
  className = "",
  offset = 0,
}: ParallaxSectionProps) {
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start end", "end start"],
  });

  const y = useTransform(scrollYProgress, [0, 1], [offset, offset + speed * 100]);

  return (
    <div ref={ref} className={className}>
      <motion.div style={{ y }}>{children}</motion.div>
    </div>
  );
}

interface ParallaxLayersProps {
  layers: {
    content: ReactNode;
    speed: number;
    zIndex?: number;
  }[];
  className?: string;
}

function ParallaxLayer({
  layer,
  index,
  scrollYProgress,
}: {
  layer: { content: ReactNode; speed: number; zIndex?: number };
  index: number;
  scrollYProgress: any;
}) {
  const y = useTransform(scrollYProgress, [0, 1], [0, layer.speed * 100]);

  return (
    <motion.div
      style={{ y, zIndex: layer.zIndex || index }}
      className="absolute inset-0"
    >
      {layer.content}
    </motion.div>
  );
}

export function ParallaxLayers({ layers, className = "" }: ParallaxLayersProps) {
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start end", "end start"],
  });

  return (
    <div ref={ref} className={`relative ${className}`}>
      {layers.map((layer, index) => (
        <ParallaxLayer
          key={index}
          layer={layer}
          index={index}
          scrollYProgress={scrollYProgress}
        />
      ))}
    </div>
  );
}
