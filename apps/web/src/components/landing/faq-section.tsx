"use client";

import { motion } from "framer-motion";
import { Plus, Minus } from "lucide-react";
import { useState } from "react";

const FAQS = [
  {
    question: "How can you deliver a landing page in just 3 days?",
    answer:
      "We've built a focused, hands-on process that cuts out unnecessary back-and-forth while keeping the quality high. Our team works closely on every project from start to finish. Most agencies spend weeks on revisions — we get it right the first time.",
  },
  {
    question: "What does the $1,000 include exactly?",
    answer:
      "Everything you need to launch: a complete custom landing page built for your brand, mobile-optimised, fast-loading, SEO-ready, and with a contact form set up. You own all the code and assets outright. The full scope is confirmed on our call before any payment.",
  },
  {
    question: "What if I need more than one page?",
    answer:
      "No problem. We handle multi-page projects too. The $1,000 covers your core landing page — if you need additional pages or specific features, we scope that together on the call and agree on a price before we start.",
  },
  {
    question: "Do I own the website after purchase?",
    answer:
      "Yes, fully. You receive complete ownership of all design files, code, and assets. Hosting is separate — we can discuss options on the call, or you can deploy to your own provider.",
  },
  {
    question: "What happens after delivery?",
    answer:
      "Your package includes 7 days of post-launch support. Anything beyond that — ongoing updates, hosting, maintenance — we can cover in your agreement. We'll go through all of this on the call.",
  },
  {
    question: "What happens if I'm not satisfied?",
    answer:
      "We stand behind our work with a 100% satisfaction guarantee. If we don't deliver what we agreed, you get a full refund within the first 7 days. No questions asked.",
  },
  {
    question: "How does the process work after the call?",
    answer:
      "We get on a free 30-minute call, align on your goals, scope, and any extras. Once we agree, you'll receive a summary and payment link. Work starts as soon as payment is confirmed, and you'll have your site live within 3 days.",
  },
  {
    question: "What do I need to prepare for the call?",
    answer:
      "Just a rough idea of your business, who your customers are, and what you want the site to do. If you have a logo or brand colours, great — but not required. We'll guide you through everything.",
  },
];

export function FAQSection() {
  const [openIndex, setOpenIndex] = useState<number | null>(0);

  return (
    <section className="relative px-6 py-24">
      <div className="max-w-4xl mx-auto">
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          transition={{ duration: 0.8 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <h2 className="text-5xl font-bold mb-4">
            Frequently Asked <span className="text-yellow-500">Questions</span>
          </h2>
          <p className="text-xl text-slate-400">
            Everything you need to know about our service
          </p>
        </motion.div>

        <div className="space-y-4">
          {FAQS.map((faq, i) => {
            const isOpen = openIndex === i;

            return (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05, duration: 0.5 }}
                viewport={{ once: true }}
              >
                <button
                  onClick={() => setOpenIndex(isOpen ? null : i)}
                  className="w-full text-left p-6 rounded-2xl bg-white/5 md:backdrop-blur-sm border border-white/10 [@media(hover:hover)]:hover:border-yellow-500/50 md:transition-all group"
                >
                  <div className="flex items-start justify-between gap-4">
                    <h3 className="text-lg font-semibold text-white pr-8 [@media(hover:hover)]:group-hover:text-yellow-500 transition-colors">
                      {faq.question}
                    </h3>
                    <div className="flex-shrink-0 w-6 h-6 rounded-full bg-yellow-500/20 flex items-center justify-center text-yellow-500 group-hover:bg-yellow-500 group-hover:text-white transition-all">
                      {isOpen ? (
                        <Minus className="w-4 h-4" />
                      ) : (
                        <Plus className="w-4 h-4" />
                      )}
                    </div>
                  </div>

                  <motion.div
                    initial={false}
                    animate={{
                      height: isOpen ? "auto" : 0,
                      opacity: isOpen ? 1 : 0,
                    }}
                    transition={{ duration: 0.3 }}
                    className="overflow-hidden"
                  >
                    <p className="text-slate-400 mt-4 leading-relaxed">
                      {faq.answer}
                    </p>
                  </motion.div>
                </button>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
