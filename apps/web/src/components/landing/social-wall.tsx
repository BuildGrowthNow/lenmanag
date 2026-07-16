"use client";

import { useEffect, useRef, useState } from "react";
import { Star } from "lucide-react";

const CUSTOMERS = [
  {
    id: 1,
    name: "Sarah",
    title: "Coffee Shop Owner",
    avatar: "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=80&h=80&fit=crop&crop=face",
    text: "Honestly, I was skeptical about the 3-day timeline. But they delivered exactly what I needed and my online orders have been crazy since launch.",
    rating: 5,
  },
  {
    id: 2,
    name: "Marcus",
    title: "Personal Trainer",
    avatar: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=80&h=80&fit=crop&crop=face",
    text: "I was losing clients to gyms with better websites. This changed everything. Now people book sessions right from my site.",
    rating: 5,
  },
  {
    id: 3,
    name: "Emma",
    title: "Interior Designer",
    avatar: "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=80&h=80&fit=crop&crop=face",
    text: "The portfolio section is gorgeous. My clients are so impressed before we even meet. Definitely helped me land bigger projects.",
    rating: 5,
  },
  {
    id: 4,
    name: "James",
    title: "Real Estate Agent",
    avatar: "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=80&h=80&fit=crop&crop=face",
    text: "Not gonna lie, I'm not tech savvy but the site works perfectly. My listings look amazing and I'm getting more showings.",
    rating: 4,
  },
  {
    id: 5,
    name: "Lisa",
    title: "Yoga Instructor",
    avatar: "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=80&h=80&fit=crop&crop=face",
    text: "Best investment for my business. Classes are booked solid and people keep mentioning how professional the website looks.",
    rating: 5,
  },
  {
    id: 6,
    name: "David",
    title: "Contractor",
    avatar: "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=80&h=80&fit=crop&crop=face",
    text: "Needed a site fast. They delivered. No complaints. My phone's ringing more now. That's all that matters.",
    rating: 4,
  },
  {
    id: 7,
    name: "Rachel",
    title: "Wedding Planner",
    avatar: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=80&h=80&fit=crop&crop=face",
    text: "Clients love booking through the site. It makes me look so much more professional. I've doubled my business in 3 months.",
    rating: 5,
  },
  {
    id: 8,
    name: "Michael",
    title: "Consultant",
    avatar: "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=80&h=80&fit=crop&crop=face",
    text: "The speed of delivery was insane. Quality is top-notch. I'm already recommending them to everyone I know.",
    rating: 5,
  },
  {
    id: 9,
    name: "Jessica",
    title: "Freelance Writer",
    avatar: "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=80&h=80&fit=crop&crop=face",
    text: "Honestly thought it would be generic but it's totally personalized to my brand. Love it. My rates went up.",
    rating: 5,
  },
  {
    id: 10,
    name: "Alex",
    title: "Photography Studio",
    avatar: "https://images.unsplash.com/photo-1519345182560-3f2917c472ef?w=80&h=80&fit=crop&crop=face",
    text: "Portfolio looks incredible. Getting inquiries from bigger clients now. Best money spent.",
    rating: 5,
  },
  {
    id: 11,
    name: "Sophie",
    title: "Chef / Catering",
    avatar: "https://images.unsplash.com/photo-1487412720507-e7ab37603c6f?w=80&h=80&fit=crop&crop=face",
    text: "People can actually see my food now with great photos. Bookings went through the roof. Super happy.",
    rating: 5,
  },
  {
    id: 12,
    name: "Tom",
    title: "Business Coach",
    avatar: "https://images.unsplash.com/photo-1463453091185-61582044d556?w=80&h=80&fit=crop&crop=face",
    text: "The testimonials section on my site converts like crazy. This was exactly what I needed.",
    rating: 4,
  },
  {
    id: 13,
    name: "Olivia",
    title: "Bakery Owner",
    avatar: "https://images.unsplash.com/photo-1531746020798-e6953c6e8e04?w=80&h=80&fit=crop&crop=face",
    text: "My customers can order online now. Sales jumped 40% in the first month. Totally worth every penny.",
    rating: 5,
  },
  {
    id: 14,
    name: "Daniel",
    title: "Lawyer",
    avatar: "https://images.unsplash.com/photo-1560250097-0b93528c311a?w=80&h=80&fit=crop&crop=face",
    text: "Professional look that builds trust with potential clients. I get compliments on my site constantly.",
    rating: 5,
  },
  {
    id: 15,
    name: "Nina",
    title: "Florist",
    avatar: "https://images.unsplash.com/photo-1502823403499-6ccfcf4fb453?w=80&h=80&fit=crop&crop=face",
    text: "My arrangements look stunning on the site. Wedding inquiries tripled since the new site went live.",
    rating: 5,
  },
  {
    id: 16,
    name: "Carlos",
    title: "Auto Mechanic",
    avatar: "https://images.unsplash.com/photo-1504257432389-52343af06ae3?w=80&h=80&fit=crop&crop=face",
    text: "Finally have a site my customers can find me on. Appointments are way up. Simple and effective.",
    rating: 4,
  },
  {
    id: 17,
    name: "Amanda",
    title: "Dentist",
    avatar: "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=80&h=80&fit=crop&crop=face",
    text: "Patients love being able to book online. The design is clean and trustworthy. Exactly what a medical practice needs.",
    rating: 5,
  },
  {
    id: 18,
    name: "Ryan",
    title: "Music Teacher",
    avatar: "https://images.unsplash.com/photo-1522075469751-3a6694fb2f61?w=80&h=80&fit=crop&crop=face",
    text: "Parents find me through Google now. Lesson bookings have never been higher. Great ROI.",
    rating: 5,
  },
  {
    id: 19,
    name: "Maria",
    title: "Spa Owner",
    avatar: "https://images.unsplash.com/photo-1580489944761-15a19d654956?w=80&h=80&fit=crop&crop=face",
    text: "The relaxing design perfectly matches my brand. Clients say it makes them want to visit even before they arrive.",
    rating: 5,
  },
  {
    id: 20,
    name: "Tyler",
    title: "Landscaper",
    avatar: "https://images.unsplash.com/photo-1492562080023-ab3db95bfbce?w=80&h=80&fit=crop&crop=face",
    text: "Before and after gallery on the site sells itself. Getting projects I never would have before.",
    rating: 5,
  },
  {
    id: 21,
    name: "Priya",
    title: "Accountant",
    avatar: "https://images.unsplash.com/photo-1607746882042-944635dfe10e?w=80&h=80&fit=crop&crop=face",
    text: "Tax season was so smooth with online scheduling. My clients love the convenience.",
    rating: 5,
  },
  {
    id: 22,
    name: "Jake",
    title: "Barber",
    avatar: "https://images.unsplash.com/photo-1531891437562-4301cf35b7e4?w=80&h=80&fit=crop&crop=face",
    text: "Walk-ins were fine, but now I'm booked solid every week. The site did that. Simple.",
    rating: 4,
  },
  {
    id: 23,
    name: "Hannah",
    title: "Pet Groomer",
    avatar: "https://images.unsplash.com/photo-1508214751196-bcfd4ca60f91?w=80&h=80&fit=crop&crop=face",
    text: "Pet parents trust me more with a professional site. Bookings are up 60%. Couldn't be happier.",
    rating: 5,
  },
  {
    id: 24,
    name: "Brandon",
    title: "Electrician",
    avatar: "https://images.unsplash.com/photo-1548449112-96a38a643324?w=80&h=80&fit=crop&crop=face",
    text: "My competitor had a website and I didn't. Now mine looks way better. Getting all the calls.",
    rating: 5,
  },
];

const ROW_1 = CUSTOMERS.slice(0, 8);
const ROW_2 = CUSTOMERS.slice(8, 16);
const ROW_3 = CUSTOMERS.slice(16, 24);

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

function CarouselRow({
  customers,
  direction,
  speed,
}: {
  customers: typeof CUSTOMERS;
  direction: "left" | "right";
  speed: number;
}) {
  const rowRef = useRef<HTMLDivElement>(null);
  const [hoveredId, setHoveredId] = useState<number | null>(null);
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
    <div className="overflow-hidden w-full">
      <div ref={rowRef} className="flex gap-4 will-change-transform">
        {duplicated.map((customer, i) => (
          <div
            key={`${customer.id}-${i}`}
            onMouseEnter={() => setHoveredId(customer.id)}
            onMouseLeave={() => setHoveredId(null)}
            className={`flex-shrink-0 w-72 p-4 rounded-xl border transition-all duration-300 ${
              hoveredId === customer.id
                ? "bg-white/15 border-yellow-500/50 scale-105 shadow-lg shadow-yellow-500/10 z-10"
                : hoveredId !== null
                  ? "bg-white/5 border-white/5 opacity-50 blur-[1px]"
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
  return (
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

      <div className="space-y-4">
        <CarouselRow customers={ROW_1} direction="left" speed={0.5} />
        <CarouselRow customers={ROW_2} direction="right" speed={0.4} />
        <CarouselRow customers={ROW_3} direction="left" speed={0.6} />
      </div>
    </section>
  );
}
