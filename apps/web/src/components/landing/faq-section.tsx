"use client";

import { motion } from "framer-motion";
import { Plus, Minus } from "lucide-react";
import { useState } from "react";

const FAQS = [
  {
    question: "How can LenQuant deliver my landing page in just 3 days?",
    answer:
      "We've been doing this for over 6 years. We specialize in transforming outdated websites into high-converting landing pages. Our streamlined, hands-on process eliminates unnecessary back-and-forth, allowing us to deliver high-quality results in just 3 days.",
  },
  {
    question: "What does the $1,000 include exactly?",
    answer:
      "Everything you need to launch: a complete custom landing page built for your brand, mobile-optimised, fast-loading, SEO-ready, and with a contact form set up. You own all the code and assets outright. The full scope is confirmed on our call before any payment.",
  },
  {
    question: "How does LenQuant's process work?",
    answer:
      "We developed a simple and efficient process to save you time and money. First, we'll schedule a free 30-minute call to understand your goals. Then, we'll research your niche and present the best solution for your business. Once you approve the proposal, we'll deliver your landing page within 3 days. You'll have 7 days to request revisions, and if you're not completely satisfied, we'll give you a full refund.",
  },
  {
    question: "Do I own the website after purchase?",
    answer:
      "Yes, fully. You receive full ownership of all design files, code, and assets. While we don't provide hosting, we're happy to help you connect your existing or new domain to your preferred hosting provider — or one of our recommended ones — at no extra cost. We'll guide you through the entire process from start to finish until your website is live.",
  },
  {
    question: "What if I need more than one page?",
    answer:
      "No problem. We handle multi-page projects too. The $1,000 covers your core landing page — if you need additional pages or specific features, we scope that together on the call and agree on a price before we start.",
  },
  {
    question: "What happens after delivery?",
    answer:
      "Your package includes 7 days of post-launch support. During this time, we're available to make adjustments and provide any additional help you need. The entire process takes up to 11 days: 1 day for our online meeting, 3 days to build your landing page, and 7 days for revisions and support. After that, we can continue helping with updates, hosting, and maintenance as outlined in your agreement with LenQuant.",
  },
  {
    question: "What happens if I'm not satisfied?",
    answer:
      "We have a 98% satisfaction rate — and we intend to keep it that way. If we don't deliver what we agreed, you get a full refund within the first 7 days. No questions asked.",
  },
  {
    question: "How LenQuant works?",
    answer:
      "After building more than 100 websites, we've developed a proven 11-day process. Day 1: We meet for a free 30-minute discovery call to align on your goals, project scope, and any additional requirements. After we agree on the proposal, you'll receive a project summary and payment link. 3 Days Production: We design and build your landing page — throughout the process, you'll receive previews so you can follow the progress. 7 Days Support: We provide dedicated post-delivery support, making any necessary revisions to ensure your landing page is exactly what you need.",
  },
  {
    question: "I'm ready to start! What do I need to prepare for the call?",
    answer:
      "Click the button below to get started and choose a date and time that works best for you. For our meeting, just find a quiet place where we can talk about your business. We only need a general understanding of what you do, who your customers are, and what you're looking to achieve. If you already have a website, logo, or brand colors, that's great — but it's not required. We'll guide you through the entire process.",
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
