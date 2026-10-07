"use client";

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, ChevronLeft, ChevronRight } from "lucide-react";
import Image from "next/image";

const SITES = [
  { name: "AfterImage", label: "Afterimage Digital", industry: "Art Gallery" },
  { name: "AfterLight", label: "AfterLight", industry: "Photography" },
  { name: "AuroraField", label: "Aurora Field", industry: "Creative Studio" },
  { name: "CourtEleven", label: "Court Eleven", industry: "Sports Club" },
  { name: "Drift", label: "Drift", industry: "Wellness" },
  { name: "Glyph", label: "Glyph", industry: "Design Agency" },
  { name: "KineticFoundry", label: "Kinetic Foundry", industry: "Engineering" },
  { name: "Latent Garden", label: "Latent Garden", industry: "Botanical" },
  { name: "MaisonNocturne", label: "Maison Nocturne", industry: "Luxury Brand" },
  { name: "Milkweed", label: "Milkweed", industry: "Sustainability" },
  { name: "Moss Works", label: "Moss Works", industry: "Architecture" },
  { name: "NightJar", label: "NightJar", industry: "Hospitality" },
  { name: "Nocturne", label: "Nocturne", industry: "Music" },
  { name: "NorthStar", label: "NorthStar", industry: "Consulting" },
  { name: "One Point Five", label: "One Point Five", industry: "Climate Tech" },
  { name: "Plane Object", label: "Plane Object", industry: "Industrial Design" },
  { name: "QuietMile", label: "Quiet Mile", industry: "Running" },
  { name: "RasterRush", label: "Raster Rush", industry: "Gaming" },
  { name: "RelayGlobal", label: "Relay Global", industry: "Logistics" },
  { name: "Thermal", label: "Thermal", industry: "Energy" },
  { name: "Tidepool", label: "Tidepool", industry: "Marine Science" },
  { name: "TinyGiants", label: "Tiny Giants", industry: "Startup Studio" },
  { name: "Voidunit", label: "Voidunit", industry: "Technology" },
];

const MOBILE_COL_1 = SITES.filter((_, i) => i % 2 === 0);
const MOBILE_COL_2 = SITES.filter((_, i) => i % 2 === 1);
const DESKTOP_COL_1 = SITES.filter((_, i) => i % 3 === 0);
const DESKTOP_COL_2 = SITES.filter((_, i) => i % 3 === 1);
const DESKTOP_COL_3 = SITES.filter((_, i) => i % 3 === 2);

function MarqueeColumn({
  sites,
  direction,
  speed,
  onSelect,
}: {
  sites: typeof SITES;
  direction: "up" | "down";
  speed: number;
  onSelect: (site: (typeof SITES)[0]) => void;
}) {
  const doubled = [...sites, ...sites];

  return (
    <div className="relative h-[450px] sm:h-[550px] lg:h-[700px] overflow-hidden">
      <div
        className={`flex flex-col gap-3 lg:gap-4 animate-marquee-${direction}`}
        style={
          {
            "--marquee-speed": `${speed}s`,
          } as React.CSSProperties
        }
      >
        {doubled.map((site, i) => (
          <button
            key={`${site.name}-${i}`}
            onClick={() => onSelect(site)}
            className="group relative rounded-xl overflow-hidden border border-white/10 [@media(hover:hover)]:hover:border-yellow-500/50 transition-all duration-300 flex-shrink-0 [@media(hover:hover)]:hover:scale-[1.03] focus:outline-none focus:ring-2 focus:ring-yellow-500/50"
          >
            <div className="relative w-full aspect-[16/10]">
              <Image
                src={`/sites/${site.name}/thumbnail.webp`}
                alt={`${site.label} — ${site.industry} website`}
                fill
                sizes="(max-width: 768px) 50vw, 33vw"
                className="object-cover object-top"
                loading="lazy"
              />
            </div>
            <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-100 [@media(hover:hover)]:opacity-0 [@media(hover:hover)]:group-hover:opacity-100 transition-opacity duration-300" />
            <div className="absolute bottom-0 left-0 right-0 p-2 lg:p-3 translate-y-0 [@media(hover:hover)]:translate-y-full [@media(hover:hover)]:group-hover:translate-y-0 transition-transform duration-300">
              <p className="text-xs lg:text-sm font-semibold text-white">{site.label}</p>
              <p className="text-[10px] lg:text-xs text-slate-300">{site.industry}</p>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

function SiteViewer({
  site,
  onClose,
  onPrev,
  onNext,
}: {
  site: (typeof SITES)[0];
  onClose: () => void;
  onPrev: () => void;
  onNext: () => void;
}) {
  const siteUrl = `/sites/${site.name}/index.html`;

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "ArrowLeft") onPrev();
      if (e.key === "ArrowRight") onNext();
    };
    window.addEventListener("keydown", handleKey);
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", handleKey);
      document.body.style.overflow = "";
    };
  }, [onClose, onPrev, onNext]);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.2 }}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 md:p-8"
    >
      <div
        className="absolute inset-0 bg-black/70 backdrop-blur-md"
        onClick={onClose}
      />

      <motion.div
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.95, opacity: 0 }}
        transition={{ duration: 0.2 }}
        className="relative w-full max-w-[90vw] h-[85vh] rounded-2xl overflow-hidden border border-white/10 bg-zinc-900 shadow-2xl"
      >
        <div className="flex items-center justify-between px-4 py-3 bg-zinc-900/95 border-b border-white/10">
          <div className="flex items-center gap-3">
            <button
              onClick={onClose}
              className="p-2 rounded-lg hover:bg-white/10 transition-colors"
              aria-label="Close viewer"
            >
              <X className="w-5 h-5 text-white" />
            </button>
            <div>
              <p className="text-sm font-semibold text-white">{site.label}</p>
              <p className="text-xs text-slate-400">{site.industry}</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={onPrev}
              className="p-2 rounded-lg hover:bg-white/10 transition-colors"
              aria-label="Previous site"
            >
              <ChevronLeft className="w-5 h-5 text-white" />
            </button>
            <button
              onClick={onNext}
              className="p-2 rounded-lg hover:bg-white/10 transition-colors"
              aria-label="Next site"
            >
              <ChevronRight className="w-5 h-5 text-white" />
            </button>
          </div>
        </div>

        <iframe
          src={siteUrl}
          className="w-full h-[calc(100%-56px)] bg-white"
          title={`${site.label} preview`}
          sandbox="allow-scripts allow-same-origin"
        />
      </motion.div>
    </motion.div>
  );
}

export function WorkShowcase() {
  const [selectedSite, setSelectedSite] = useState<(typeof SITES)[0] | null>(
    null
  );
  const [isPaused, setIsPaused] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(max-width: 767px)");
    setIsMobile(mq.matches);
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  const handleSelect = useCallback(
    (site: (typeof SITES)[0]) => {
      if (isMobile) {
        window.open(`/sites/${site.name}/index.html`, "_blank");
      } else {
        setSelectedSite(site);
      }
    },
    [isMobile]
  );

  const handlePrev = useCallback(() => {
    if (!selectedSite) return;
    const idx = SITES.findIndex((s) => s.name === selectedSite.name);
    const prev = idx <= 0 ? SITES.length - 1 : idx - 1;
    setSelectedSite(SITES[prev]);
  }, [selectedSite]);

  const handleNext = useCallback(() => {
    if (!selectedSite) return;
    const idx = SITES.findIndex((s) => s.name === selectedSite.name);
    const next = idx >= SITES.length - 1 ? 0 : idx + 1;
    setSelectedSite(SITES[next]);
  }, [selectedSite]);

  return (
    <section id="examples" className="relative px-6 py-24">
      <div className="max-w-7xl mx-auto">
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          transition={{ duration: 0.8 }}
          viewport={{ once: true }}
          className="text-center mb-12"
        >
          <h2 className="text-5xl font-bold mb-4">
            See Our <span className="text-yellow-500">Work</span>
          </h2>
          <p className="text-xl text-slate-400">
            Examples of what we can build for you. Click any to explore.
          </p>
        </motion.div>

        {/* Mobile: 2 columns with all sites */}
        <div
          className="grid grid-cols-2 gap-3 lg:hidden"
          onMouseEnter={() => setIsPaused(true)}
          onMouseLeave={() => setIsPaused(false)}
        >
          <div className={isPaused ? "paused" : ""}>
            <MarqueeColumn
              sites={MOBILE_COL_1}
              direction="up"
              speed={45}
              onSelect={handleSelect}
            />
          </div>
          <div className={isPaused ? "paused" : ""}>
            <MarqueeColumn
              sites={MOBILE_COL_2}
              direction="down"
              speed={50}
              onSelect={handleSelect}
            />
          </div>
        </div>

        {/* Desktop: 3 columns */}
        <div
          className="hidden lg:grid lg:grid-cols-3 gap-4"
          onMouseEnter={() => setIsPaused(true)}
          onMouseLeave={() => setIsPaused(false)}
        >
          <div className={isPaused ? "paused" : ""}>
            <MarqueeColumn
              sites={DESKTOP_COL_1}
              direction="up"
              speed={35}
              onSelect={handleSelect}
            />
          </div>
          <div className={isPaused ? "paused" : ""}>
            <MarqueeColumn
              sites={DESKTOP_COL_2}
              direction="down"
              speed={40}
              onSelect={handleSelect}
            />
          </div>
          <div className={isPaused ? "paused" : ""}>
            <MarqueeColumn
              sites={DESKTOP_COL_3}
              direction="up"
              speed={38}
              onSelect={handleSelect}
            />
          </div>
        </div>
      </div>

      <AnimatePresence>
        {selectedSite && (
          <SiteViewer
            site={selectedSite}
            onClose={() => setSelectedSite(null)}
            onPrev={handlePrev}
            onNext={handleNext}
          />
        )}
      </AnimatePresence>
    </section>
  );
}
