"use client";

import { motion } from "framer-motion";
import { Star, Quote } from "lucide-react";
import { Card } from "@/components/ui/card";
import { useSupportsHover } from "@/hooks/use-supports-hover";

const TESTIMONIALS = [
  {
    name: "Marcus Williams",
    role: "CEO, TechVenture Solutions",
    avatar: "MW",
    rating: 5,
    text: "Conversions up 40% in two months. Worth every dollar.",
    gradient: "from-blue-500 to-cyan-500",
  },
  {
    name: "Sophia Chen",
    role: "Founder, GreenLeaf Organics",
    avatar: "SC",
    rating: 5,
    text: "Honestly didn't believe the 3-day promise. They delivered in 2. Design is clean, customers keep complimenting it, and I didn't have to chase anyone once.",
    gradient: "from-green-500 to-emerald-500",
  },
  {
    name: "Jordan Blake",
    role: "Marketing Director, Apex Digital",
    avatar: "JB",
    rating: 5,
    text: "On time. No back-and-forth. SEO alone paid for it.",
    gradient: "from-purple-500 to-pink-500",
  },
  {
    name: "Elena Rodriguez",
    role: "Owner, Coastal Realty Group",
    avatar: "ER",
    rating: 5,
    text: "I've worked with three agencies before LenQuant. This was the first time I didn't have to explain myself twice. They got it right on the first preview and the whole process felt effortless.",
    gradient: "from-orange-500 to-red-500",
  },
  {
    name: "David Park",
    role: "CTO, CloudSync Systems",
    avatar: "DP",
    rating: 5,
    text: "Fast, clean code, mobile-ready. These guys know what they're doing.",
    gradient: "from-indigo-500 to-blue-500",
  },
  {
    name: "Rachel Thompson",
    role: "Creative Director, Artisan Studios",
    avatar: "RT",
    rating: 5,
    text: "I'm a designer. I'm picky. They still impressed me.",
    gradient: "from-pink-500 to-rose-500",
  },
];

export function TestimonialsSection() {
  const supportsHover = useSupportsHover();

  return (
    <section className="relative px-6 py-24 overflow-hidden">
      <div className="max-w-7xl mx-auto">
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          transition={{ duration: 0.8 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <h2 className="text-5xl font-bold mb-4">
            Loved by <span className="text-yellow-500">Business Owners</span>
          </h2>
          <p className="text-xl text-slate-400">
            Join hundreds of satisfied clients transforming their online presence
          </p>
        </motion.div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {TESTIMONIALS.map((testimonial, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1, duration: 0.5 }}
              viewport={{ once: true, amount: 0.3 }}
              {...(supportsHover && { whileHover: { y: -8, scale: 1.02 } })}
            >
              <Card className="p-6 h-full bg-white/5 border-white/10 [@media(hover:hover)]:hover:border-yellow-500/50 md:transition-all duration-300 [@media(hover:hover)]:hover:shadow-xl [@media(hover:hover)]:hover:shadow-yellow-500/10 relative overflow-hidden group will-change-transform">
                <Quote className="absolute top-4 right-4 w-12 h-12 text-yellow-500/10" />

                <div className="flex gap-1 mb-4">
                  {Array.from({ length: testimonial.rating }, (_, i) => (
                    <Star
                      key={i}
                      className="w-4 h-4 fill-yellow-500 text-yellow-500"
                    />
                  ))}
                </div>

                <p className="text-slate-300 mb-6 leading-relaxed relative z-10">
                  &quot;{testimonial.text}&quot;
                </p>

                <div className="flex items-center gap-3 relative z-10">
                  <div
                    className={`w-12 h-12 rounded-full bg-gradient-to-br ${testimonial.gradient} flex items-center justify-center shadow-lg flex-shrink-0`}
                  >
                    <span className="text-white font-bold text-sm">
                      {testimonial.avatar}
                    </span>
                  </div>
                  <div>
                    <div className="text-white font-semibold">
                      {testimonial.name}
                    </div>
                    <div className="text-sm text-slate-400">
                      {testimonial.role}
                    </div>
                  </div>
                </div>
              </Card>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
