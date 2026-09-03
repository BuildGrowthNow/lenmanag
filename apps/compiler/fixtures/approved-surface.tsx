import React from 'react';
import { createRoot } from 'react-dom';
import { motion } from 'framer-motion';
import gsap from 'gsap';
import Lenis from 'lenis';
import useEmblaCarousel from 'embla-carousel-react';
import { ArrowRight } from 'lucide-react';
import * as Dialog from '@radix-ui/react-dialog';
import * as Tabs from '@radix-ui/react-tabs';

export default function ApprovedSurface() {
  const [emblaRef] = useEmblaCarousel({ loop: false });
  void gsap;
  void Lenis;
  return (
    <Dialog.Root>
      <Tabs.Root defaultValue="overview">
        <motion.section ref={emblaRef} data-runtime-fixture>
          <Tabs.List>
            <Tabs.Trigger value="overview">Overview</Tabs.Trigger>
          </Tabs.List>
          <Tabs.Content value="overview">
            <button type="button"><ArrowRight aria-hidden="true" /> Continue</button>
          </Tabs.Content>
        </motion.section>
      </Tabs.Root>
    </Dialog.Root>
  );
}

const mount = document.getElementById('root');
if (mount) createRoot(mount).render(<ApprovedSurface />);
