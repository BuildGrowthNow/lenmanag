"use client";

import { createContext, useContext, useEffect, useRef, useState } from "react";
import { Star } from "lucide-react";

function useIsMobile() {
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(max-width: 767px)");
    setIsMobile(mq.matches);
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  return isMobile;
}

const CUSTOMERS = [
  {
    id: 1,
    name: "Sarah",
    title: "Coffee Shop Owner",
    avatar: "/avatars/sarah.jpg",
    text: "didnt believe the 3 days thing. they delivered in 2. online orders went crazy",
    rating: 5,
  },
  {
    id: 2,
    name: "Marcus",
    title: "Personal Trainer",
    avatar: "/avatars/marcus.jpg",
    text: "I was losing clients to gyms with better websites. This changed everything. People book sessions right from my site now and I didn't have to do anything after the call.",
    rating: 5,
  },
  {
    id: 3,
    name: "Emma",
    title: "Interior Designer",
    avatar: "/avatars/emma.jpg",
    text: "landing bigger projects fr",
    rating: 5,
  },
  {
    id: 4,
    name: "James",
    title: "Real Estate Agent",
    avatar: "/avatars/james.jpg",
    text: "not tech savvy at all but the site just works. listings look amazing and showings are up",
    rating: 4,
  },
  {
    id: 5,
    name: "Lisa",
    title: "Yoga Instructor",
    avatar: "/avatars/lisa.jpg",
    text: "Classes booked solid every week. Best money I spent on my business no cap",
    rating: 5,
  },
  {
    id: 6,
    name: "David",
    title: "Contractor",
    avatar: "/avatars/david.jpg",
    text: "needed it fast. got it fast. phone hasnt stopped ringing",
    rating: 4,
  },
  {
    id: 7,
    name: "Rachel",
    title: "Wedding Planner",
    avatar: "/avatars/rachel.jpg",
    text: "Doubled my bookings in 3 months. I keep saying it to everyone who asks how I did it.",
    rating: 5,
  },
  {
    id: 8,
    name: "Michael",
    title: "Consultant",
    avatar: "/avatars/michael.jpg",
    text: "speed was insane. quality too. already sent 3 people their way",
    rating: 5,
  },
  {
    id: 9,
    name: "Jessica",
    title: "Freelance Writer",
    avatar: "/avatars/jessica.jpg",
    text: "thought it would be generic. it wasnt. totally my brand. raised my rates right after",
    rating: 5,
  },
  {
    id: 10,
    name: "Alex",
    title: "Photography Studio",
    avatar: "/avatars/alex.jpg",
    text: "Portfolio hits different now. Bigger clients, better projects. Worth every dollar.",
    rating: 5,
  },
  {
    id: 11,
    name: "Sophie",
    title: "Chef / Catering",
    avatar: "/avatars/sophie.jpg",
    text: "bookings through the roof. people see the food and just buy. simple",
    rating: 5,
  },
  {
    id: 12,
    name: "Tom",
    title: "Business Coach",
    avatar: "/avatars/tom.jpg",
    text: "Exactly what I needed. No fluff, no back and forth. They just got it.",
    rating: 4,
  },
  {
    id: 13,
    name: "Olivia",
    title: "Bakery Owner",
    avatar: "/avatars/olivia.jpg",
    text: "sales up 40% first month. customers order online now. totally worth it",
    rating: 5,
  },
  {
    id: 14,
    name: "Daniel",
    title: "Lawyer",
    avatar: "/avatars/daniel.jpg",
    text: "Clients trust me before we even speak. The site does that. I get compliments on it constantly.",
    rating: 5,
  },
  {
    id: 15,
    name: "Nina",
    title: "Florist",
    avatar: "/avatars/nina.jpg",
    text: "wedding inquiries tripled. not kidding",
    rating: 5,
  },
  {
    id: 16,
    name: "Carlos",
    title: "Auto Mechanic",
    avatar: "/avatars/carlos.jpg",
    text: "customers can find me now. appointments way up. does what it needs to do",
    rating: 4,
  },
  {
    id: 17,
    name: "Amanda",
    title: "Dentist",
    avatar: "/avatars/amanda.jpg",
    text: "Patients book online, show up prepared, trust the practice before walking in. Exactly what we needed.",
    rating: 5,
  },
  {
    id: 18,
    name: "Ryan",
    title: "Music Teacher",
    avatar: "/avatars/ryan.jpg",
    text: "parents find me on google now. lesson bookings never been higher",
    rating: 5,
  },
  {
    id: 19,
    name: "Maria",
    title: "Spa Owner",
    avatar: "/avatars/maria.jpg",
    text: "clients say the site makes them want to come in before they even book. thats the vibe we wanted",
    rating: 5,
  },
  {
    id: 20,
    name: "Tyler",
    title: "Landscaper",
    avatar: "/avatars/tyler.jpg",
    text: "gallery sells itself. getting projects I never wouldve gotten before",
    rating: 5,
  },
  {
    id: 21,
    name: "Priya",
    title: "Accountant",
    avatar: "/avatars/priya.jpg",
    text: "Tax season ran so smooth this year. Online scheduling changed everything for my practice.",
    rating: 5,
  },
  {
    id: 22,
    name: "Jake",
    title: "Barber",
    avatar: "/avatars/jake.jpg",
    text: "booked solid every week now. the site did that",
    rating: 4,
  },
  {
    id: 23,
    name: "Hannah",
    title: "Pet Groomer",
    avatar: "/avatars/hannah.jpg",
    text: "up 60% on bookings. pet parents trust me more with a proper site. couldnt be happier fr",
    rating: 5,
  },
  {
    id: 24,
    name: "Brandon",
    title: "Electrician",
    avatar: "/avatars/brandon.jpg",
    text: "my competitor had a site and I didnt. now mine looks way better. getting all the calls",
    rating: 5,
  },
];

const ROW_1 = CUSTOMERS.slice(0, 8);
const ROW_2 = CUSTOMERS.slice(8, 16);
const ROW_3 = CUSTOMERS.slice(16, 24);

// Context to share hover state across all carousel rows
const HoverContext = createContext<{
  hoveredId: number | null;
  setHoveredId: (id: number | null) => void;
}>({ hoveredId: null, setHoveredId: () => {} });

function useHoverContext() {
  return useContext(HoverContext);
}

function StarRating({ rating }: { rating: number }) {
  return (
    <div className="flex gap-0.5">
      {Array.from({ length: 5 }).map((_, i) => (
        <Star
          key={i}
          size={12}
          className={i < rating ? "fill-yellow-400 text-yellow-400" : "text-zinc-600"}
        />
      ))}
    </div>
  );
}

function MobileCarouselRow({
  customers,
  direction,
  duration,
}: {
  customers: typeof CUSTOMERS;
  direction: "left" | "right";
  duration: number;
}) {
  const duplicated = [...customers, ...customers];
  const animationName = direction === "left" ? "scroll-left" : "scroll-right";

  return (
    <div className="overflow-hidden w-full">
      <div
        className="flex gap-3 will-change-transform"
        style={{
          animation: `${animationName} ${duration}s linear infinite`,
        }}
      >
        {duplicated.map((customer, i) => (
          <div
            key={`${customer.id}-${i}`}
            className="flex-shrink-0 w-60 p-3 rounded-xl border bg-white/5 border-white/10"
          >
            <div className="flex items-center gap-3 mb-2">
              <div className="w-8 h-8 rounded-full overflow-hidden flex-shrink-0 border border-white/20">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={customer.avatar}
                  alt={customer.name}
                  className="w-full h-full object-cover"
                />
              </div>
              <div>
                <h4 className="font-semibold text-white text-xs">{customer.name}</h4>
                <p className="text-[10px] text-zinc-400">{customer.title}</p>
              </div>
            </div>
            <StarRating rating={customer.rating} />
            <p className="text-zinc-300 text-[11px] leading-relaxed mt-1.5 line-clamp-3">
              &quot;{customer.text}&quot;
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

function DesktopCarouselRow({
  customers,
  direction,
  speed,
}: {
  customers: typeof CUSTOMERS;
  direction: "left" | "right";
  speed: number;
}) {
  const rowRef = useRef<HTMLDivElement>(null);
  const { hoveredId, setHoveredId } = useHoverContext();
  const animationRef = useRef<number | null>(null);
  const scrollPos = useRef(0);

  useEffect(() => {
    const row = rowRef.current;
    if (!row) return;

    const totalWidth = row.scrollWidth / 2;

    const animate = () => {
      if (hoveredId !== null) {
        animationRef.current = requestAnimationFrame(animate);
        return;
      }

      if (direction === "left") {
        scrollPos.current += speed;
        if (scrollPos.current >= totalWidth) {
          scrollPos.current -= totalWidth;
        }
      } else {
        scrollPos.current -= speed;
        if (scrollPos.current <= 0) {
          scrollPos.current += totalWidth;
        }
      }

      row.style.transform = `translateX(-${scrollPos.current}px)`;
      animationRef.current = requestAnimationFrame(animate);
    };

    animationRef.current = requestAnimationFrame(animate);
    return () => {
      if (animationRef.current) cancelAnimationFrame(animationRef.current);
    };
  }, [direction, speed, hoveredId]);

  const duplicated = [...customers, ...customers];

  return (
    <div className="overflow-visible w-full">
      <div ref={rowRef} className="flex gap-4 will-change-transform">
        {duplicated.map((customer, i) => (
          <div
            key={`${customer.id}-${i}`}
            onMouseEnter={() => setHoveredId(customer.id)}
            onMouseLeave={() => setHoveredId(null)}
            className={`flex-shrink-0 w-72 p-4 rounded-xl border transition-all duration-300 ${
              hoveredId === customer.id
                ? "bg-white/15 border-yellow-500/50 scale-125 shadow-2xl shadow-yellow-500/20 z-50 relative"
                : hoveredId !== null
                  ? "bg-white/5 border-white/5 opacity-40 blur-sm"
                  : "bg-white/5 border-white/10"
            }`}
          >
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-full overflow-hidden flex-shrink-0 border border-white/20">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={customer.avatar}
                  alt={customer.name}
                  className="w-full h-full object-cover"
                />
              </div>
              <div>
                <h4 className="font-semibold text-white text-sm">{customer.name}</h4>
                <p className="text-xs text-zinc-400">{customer.title}</p>
              </div>
            </div>
            <StarRating rating={customer.rating} />
            <p className="text-zinc-300 text-xs leading-relaxed mt-2 line-clamp-3">
              &quot;{customer.text}&quot;
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

export function SocialWall() {
  const [hoveredId, setHoveredId] = useState<number | null>(null);
  const isMobile = useIsMobile();

  return (
    <HoverContext.Provider value={{ hoveredId, setHoveredId }}>
      <style jsx global>{`
        @keyframes scroll-left {
          from { transform: translateX(0); }
          to { transform: translateX(-50%); }
        }
        @keyframes scroll-right {
          from { transform: translateX(-50%); }
          to { transform: translateX(0); }
        }
      `}</style>
      <section className="relative py-16 overflow-hidden">
        <div className="text-center mb-10 px-6">
          <p className="text-yellow-500 text-sm font-bold uppercase mb-2">
            From Real People
          </p>
          <h2 className="text-4xl md:text-5xl font-bold text-white mb-3">
            Meet Our <span className="text-yellow-500">Happy Clients</span>
          </h2>
          <p className="text-zinc-400 text-lg">
            Real stories from people just like you
          </p>
        </div>

        {isMobile ? (
          <div className="space-y-3">
            <MobileCarouselRow customers={ROW_1} direction="left" duration={60} />
            <MobileCarouselRow customers={ROW_2} direction="right" duration={70} />
            <MobileCarouselRow customers={ROW_3} direction="left" duration={65} />
          </div>
        ) : (
          <div className="space-y-4">
            <DesktopCarouselRow customers={ROW_1} direction="left" speed={0.5} />
            <DesktopCarouselRow customers={ROW_2} direction="right" speed={0.4} />
            <DesktopCarouselRow customers={ROW_3} direction="left" speed={0.6} />
          </div>
        )}
      </section>
    </HoverContext.Provider>
  );
}
