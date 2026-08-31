import { useEffect } from 'react';
import { motion } from 'framer-motion';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import Lenis from 'lenis';
import useEmblaCarousel from 'embla-carousel-react';
import { ArrowRight } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';

export default function CapabilityFixture() {
  useEffect(() => {
    gsap.registerPlugin(ScrollTrigger);
    const lenis = new Lenis();
    const frame = (time: number) => { lenis.raf(time); };
    lenis.on('scroll', ScrollTrigger.update);
    gsap.ticker.add(frame);
    return () => { gsap.ticker.remove(frame); lenis.destroy(); };
  }, []);
  const [emblaRef] = useEmblaCarousel();
  return <motion.main animate={{ opacity: 1 }} className="grid grid-cols-[minmax(0,1fr)_240px] gap-[37px] md:hover:scale-[1.01]" ref={emblaRef}>
    <Card><Badge>Supported</Badge><Button><ArrowRight /></Button><Separator /></Card>
  </motion.main>;
}
