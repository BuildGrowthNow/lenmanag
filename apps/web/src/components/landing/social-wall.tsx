"use client";

import { motion } from "framer-motion";
import { useState, useRef, useEffect } from "react";
import { Star } from "lucide-react";

const CUSTOMERS = [
  {
    id: 1,
    name: "Sarah",
    title: "Coffee Shop Owner",
    avatar: "https://api.multiavatar.com/sarah_coffee.svg",
    text: "Honestly, I was skeptical about the 3-day timeline. But they delivered exactly what I needed and my online orders have been crazy since launch. So worth it!",
    rating: 5,
  },
  {
    id: 2,
    name: "Marcus",
    title: "Personal Trainer",
    avatar: "https://api.multiavatar.com/marcus_trainer.svg",
    text: "I was losing clients to gyms with better websites. This changed everything. Now people book sessions right from my site.",
    rating: 5,
  },
  {
    id: 3,
    name: "Emma",
    title: "Interior Designer",
    avatar: "https://api.multiavatar.com/emma_designer.svg",
    text: "The portfolio section is gorgeous. My clients are so impressed before we even meet. Definitely helped me land bigger projects.",
    rating: 5,
  },
  {
    id: 4,
    name: "James",
    title: "Real Estate Agent",
    avatar: "https://api.multiavatar.com/james_realtor.svg",
    text: "Not gonna lie, I'm not tech savvy but the site works perfectly. My listings look amazing and I'm getting more showings.",
    rating: 4,
  },
  {
    id: 5,
    name: "Lisa",
    title: "Yoga Instructor",
    avatar: "https://api.multiavatar.com/lisa_yoga.svg",
    text: "Best investment for my business. Classes are booked solid and people keep mentioning how professional the website looks.",
    rating: 5,
  },
  {
    id: 6,
    name: "David",
    title: "Contractor",
    avatar: "https://api.multiavatar.com/david_build.svg",
    text: "Needed a site fast. They delivered. No complaints. My phone's ringing more now. That's all that matters.",
    rating: 4,
  },
  {
    id: 7,
    name: "Rachel",
    title: "Wedding Planner",
    avatar: "https://api.multiavatar.com/rachel_wedding.svg",
    text: "Clients love booking through the site. It makes me look so much more professional. I've doubled my business in 3 months.",
    rating: 5,
  },
  {
    id: 8,
    name: "Michael",
    title: "Consultant",
    avatar: "https://api.multiavatar.com/michael_consult.svg",
    text: "The speed of delivery was insane. Quality is top-notch. I'm already recommending them to everyone I know.",
    rating: 5,
  },
  {
    id: 9,
    name: "Jessica",
    title: "Freelance Writer",
    avatar: "https://api.multiavatar.com/jessica_writer.svg",
    text: "Honestly thought it would be generic but it's totally personalized to my brand. Love it. My rates went up.",
    rating: 5,
  },
  {
    id: 10,
    name: "Alex",
    title: "Photography Studio",
    avatar: "https://api.multiavatar.com/alex_photo.svg",
    text: "Portfolio looks incredible. Getting inquiries from bigger clients now. Best money spent.",
    rating: 5,
  },
  {
    id: 11,
    name: "Sophie",
    title: "Chef / Catering",
    avatar: "https://api.multiavatar.com/sophie_chef.svg",
    text: "People can actually see my food now with great photos. Bookings went through the roof. Super happy.",
    rating: 5,
  },
  {
    id: 12,
    name: "Tom",
    title: "Business Coach",
    avatar: "https://api.multiavatar.com/tom_coach.svg",
    text: "The testimonials section on my site converts like crazy. This was exactly what I needed. Legit.",
    rating: 4,
  },
];

export function SocialWall() {
  const [hoveredId, setHoveredId] = useState<number | null>(null);
  const [isScrolling, setIsScrolling] = useState(true);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current || !isScrolling) return;

    const container = containerRef.current;
    let scrollAmount = 0;
    const scrollSpeed = 1;

    const interval = setInterval(() => {
      scrollAmount += scrollSpeed;
      if (container.scrollLeft >= container.scrollWidth - container.clientWidth) {
        scrollAmount = 0;
        container.scrollLeft = 0;
      } else {
        container.scrollLeft += scrollSpeed;
      }
    }, 30);

    return () => clearInterval(interval);
  }, [isScrolling]);

  const StarRating = ({ rating }: { rating: number }) => (
    <div className="flex gap-1">
      {Array.from({ length: 5 }).map((_, i) => (
        <Star
          key={i}
          size={16}
          className={i < rating ? "fill-yellow-400 text-yellow-400" : "text-zinc-600"}
        />
      ))}
    </div>
  );

  return (
    <section className="relative px-6 py-24 bg-zinc-900/50">
      <div className="max-w-7xl mx-auto">
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          transition={{ duration: 0.8 }}
          viewport={{ once: true }}
          className="text-center mb-12"
        >
          <p className="text-yellow-500 text-sm font-bold uppercase mb-2">
            From Real People
          </p>
          <h2 className="text-5xl font-bold text-white mb-4">
            Meet Our <span className="text-yellow-500">Happy Clients</span>
          </h2>
          <p className="text-zinc-400 text-lg">
            Scroll through real stories from people just like you
          </p>
        </motion.div>

        {/* Scrolling Container */}
        <div className="relative">
          <motion.div
            ref={containerRef}
            onMouseEnter={() => setIsScrolling(false)}
            onMouseLeave={() => setIsScrolling(true)}
            className="flex gap-6 overflow-x-auto pb-6 scroll-smooth hide-scrollbar"
            style={{ scrollBehavior: "smooth" }}
          >
            {CUSTOMERS.map((customer, index) => (
              <motion.div
                key={customer.id}
                onMouseEnter={() => setHoveredId(customer.id)}
                onMouseLeave={() => setHoveredId(null)}
                animate={{
                  scale: hoveredId === customer.id ? 1.1 : hoveredId ? 0.9 : 1,
                  opacity: hoveredId === customer.id ? 1 : hoveredId ? 0.5 : 1,
                }}
                transition={{ duration: 0.3 }}
                className="flex-shrink-0 w-80 group cursor-pointer"
              >
                <motion.div
                  className="p-6 rounded-2xl bg-gradient-to-br from-white/10 to-white/5 border border-white/10 hover:border-yellow-500/50 transition-all h-full"
                  whileHover={{
                    boxShadow: "0 0 30px rgba(250, 204, 21, 0.2)",
                  }}
                >
                  {/* Avatar and Info */}
                  <div className="flex items-center gap-4 mb-4">
                    <motion.div
                      animate={{
                        scale: hoveredId === customer.id ? 1.15 : 1,
                      }}
                      className="relative flex-shrink-0"
                    >
                      <div className="w-16 h-16 rounded-full bg-gradient-to-br from-yellow-400 to-orange-500 p-0.5 overflow-hidden">
                        <img
                          src={customer.avatar}
                          alt={customer.name}
                          className="w-full h-full rounded-full object-cover bg-zinc-700"
                        />
                      </div>
                      <motion.div
                        animate={{
                          scale: hoveredId === customer.id ? 1 : 0,
                        }}
                        className="absolute inset-0 rounded-full border-2 border-yellow-400"
                      />
                    </motion.div>

                    <div>
                      <h4 className="font-bold text-white text-lg">
                        {customer.name}
                      </h4>
                      <p className="text-sm text-zinc-400">{customer.title}</p>
                    </div>
                  </div>

                  {/* Stars */}
                  <div className="mb-4">
                    <StarRating rating={customer.rating} />
                  </div>

                  {/* Testimonial */}
                  <motion.p
                    animate={{
                      opacity: hoveredId === customer.id ? 1 : 1,
                    }}
                    className="text-zinc-300 text-sm leading-relaxed italic"
                  >
                    "{customer.text}"
                  </motion.p>

                  {/* Hover Indicator */}
                  <motion.div
                    animate={{
                      opacity: hoveredId === customer.id ? 1 : 0,
                    }}
                    className="mt-4 pt-4 border-t border-yellow-500/30 text-center"
                  >
                    <span className="text-xs text-yellow-500 font-semibold">
                      ✓ Verified Customer
                    </span>
                  </motion.div>
                </motion.div>
              </motion.div>
            ))}
          </motion.div>

          {/* Gradient Overlays */}
          <div className="absolute left-0 top-0 bottom-0 w-20 bg-gradient-to-r from-zinc-950 to-transparent pointer-events-none z-10" />
          <div className="absolute right-0 top-0 bottom-0 w-20 bg-gradient-to-l from-zinc-950 to-transparent pointer-events-none z-10" />
        </div>

        {/* Info Text */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="text-center text-zinc-400 text-sm mt-8"
        >
          Hover to zoom in • Scroll to see more • Real people, real results
        </motion.p>
      </div>

      <style jsx>{`
        .hide-scrollbar {
          -ms-overflow-style: none;
          scrollbar-width: none;
        }
        .hide-scrollbar::-webkit-scrollbar {
          display: none;
        }
      `}</style>
    </section>
  );
}
