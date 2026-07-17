"use client";

import { useEffect, useState } from "react";

/**
 * Detects if the device supports precise hover (mouse/trackpad) vs touch.
 * Returns false on mobile/touch devices to prevent hover animations from
 * firing during scroll, which causes visual glitches.
 */
export function useSupportsHover(): boolean {
  const [supportsHover, setSupportsHover] = useState(true);

  useEffect(() => {
    const mediaQuery = window.matchMedia("(hover: hover) and (pointer: fine)");
    setSupportsHover(mediaQuery.matches);

    const handler = (e: MediaQueryListEvent) => setSupportsHover(e.matches);
    mediaQuery.addEventListener("change", handler);
    return () => mediaQuery.removeEventListener("change", handler);
  }, []);

  return supportsHover;
}
