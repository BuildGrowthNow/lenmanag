'use client';

import { useEffect, useRef } from 'react';

export function CursorGlow() {
  const ref = useRef<HTMLDivElement>(null);
  const visible = useRef(false);

  useEffect(() => {
    const HALF = 150;

    const onMove = (e: MouseEvent) => {
      if (!ref.current) return;
      if (!visible.current) {
        ref.current.style.opacity = '1';
        visible.current = true;
      }
      ref.current.style.transform = `translate(${e.clientX - HALF}px, ${e.clientY - HALF}px)`;
    };

    const onLeave = () => {
      if (ref.current) ref.current.style.opacity = '0';
      visible.current = false;
    };

    window.addEventListener('mousemove', onMove);
    document.documentElement.addEventListener('mouseleave', onLeave);
    return () => {
      window.removeEventListener('mousemove', onMove);
      document.documentElement.removeEventListener('mouseleave', onLeave);
    };
  }, []);

  return (
    <div
      ref={ref}
      aria-hidden="true"
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: 300,
        height: 300,
        borderRadius: '50%',
        background: 'radial-gradient(circle, rgba(234, 179, 8, 0.09) 0%, rgba(234, 179, 8, 0.03) 45%, transparent 70%)',
        pointerEvents: 'none',
        zIndex: 9999,
        opacity: 0,
        transition: 'transform 0.12s ease-out, opacity 0.4s ease',
        willChange: 'transform',
      }}
    />
  );
}
