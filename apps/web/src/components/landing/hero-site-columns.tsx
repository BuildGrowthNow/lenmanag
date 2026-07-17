"use client";

import { useEffect, useState } from "react";
import Image from "next/image";

const LEFT_COL_1 = [
  "AfterImage",
  "Drift",
  "KineticFoundry",
  "Nocturne",
  "QuietMile",
  "Thermal",
];
const LEFT_COL_2 = [
  "AfterLight",
  "Glyph",
  "MaisonNocturne",
  "NorthStar",
  "RasterRush",
  "Tidepool",
];
const RIGHT_COL_1 = [
  "AuroraField",
  "CourtEleven",
  "Latent Garden",
  "Milkweed",
  "One Point Five",
  "RelayGlobal",
];
const RIGHT_COL_2 = [
  "Moss Works",
  "NightJar",
  "Plane Object",
  "TinyGiants",
  "Voidunit",
  "Thermal",
];

function Column({
  sites,
  direction,
  speed,
}: {
  sites: string[];
  direction: "up" | "down";
  speed: number;
}) {
  const doubled = [...sites, ...sites];

  return (
    <div className="relative h-full overflow-hidden">
      <div
        className={`flex flex-col gap-4 animate-marquee-${direction}`}
        style={{ "--marquee-speed": `${speed}s` } as React.CSSProperties}
      >
        {doubled.map((name, i) => (
          <div
            key={`${name}-${i}`}
            className="relative w-full aspect-[16/10] rounded-lg overflow-hidden flex-shrink-0"
          >
            <Image
              src={`/sites/${name}/thumbnail.webp`}
              alt=""
              fill
              sizes="300px"
              className="object-cover object-top"
              loading="eager"
            />
          </div>
        ))}
      </div>
    </div>
  );
}

export function HeroSiteColumns() {
  const [opacity, setOpacity] = useState(1);

  useEffect(() => {
    let rafId: number;
    let currentOpacity = 1;

    const handleScroll = () => {
      cancelAnimationFrame(rafId);
      rafId = requestAnimationFrame(() => {
        const scrollY = window.scrollY;
        const fadeStart = 50;
        const fadeEnd = 800;

        let target: number;
        if (scrollY <= fadeStart) {
          target = 1;
        } else if (scrollY >= fadeEnd) {
          target = 0;
        } else {
          target = 1 - (scrollY - fadeStart) / (fadeEnd - fadeStart);
        }

        currentOpacity = currentOpacity + (target - currentOpacity) * 0.15;
        if (Math.abs(currentOpacity - target) < 0.01) currentOpacity = target;
        setOpacity(currentOpacity);
      });
    };

    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => {
      window.removeEventListener("scroll", handleScroll);
      cancelAnimationFrame(rafId);
    };
  }, []);

  if (opacity === 0) return null;

  return (
    <div
      className="fixed inset-0 pointer-events-none overflow-hidden hidden xl:block z-0 transition-opacity duration-300 ease-out"
      aria-hidden="true"
      style={{ opacity }}
    >
      {/* Left side — 2 columns */}
      <div className="absolute left-0 top-0 bottom-0 w-[540px] flex gap-3 pl-4 opacity-[0.15] blur-[1.5px]">
        <div className="flex-1 h-full">
          <Column sites={LEFT_COL_1} direction="up" speed={50} />
        </div>
        <div className="flex-1 h-full">
          <Column sites={LEFT_COL_2} direction="up" speed={58} />
        </div>
      </div>

      {/* Right side — 2 columns */}
      <div className="absolute right-0 top-0 bottom-0 w-[540px] flex gap-3 pr-4 opacity-[0.15] blur-[1.5px]">
        <div className="flex-1 h-full">
          <Column sites={RIGHT_COL_1} direction="up" speed={54} />
        </div>
        <div className="flex-1 h-full">
          <Column sites={RIGHT_COL_2} direction="up" speed={46} />
        </div>
      </div>

      {/* Fade edges so columns blend into background */}
      <div className="absolute left-0 top-0 bottom-0 w-[540px] bg-gradient-to-r from-zinc-950 via-zinc-950/40 to-transparent" />
      <div className="absolute right-0 top-0 bottom-0 w-[540px] bg-gradient-to-l from-zinc-950 via-zinc-950/40 to-transparent" />
    </div>
  );
}
