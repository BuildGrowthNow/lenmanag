"use client";

import { motion } from "framer-motion";
import { Plus, Minus } from "lucide-react";
import { useState } from "react";

const FAQS = [
  {
    question: "How can you deliver a website in just 3 days?",
    answer:
      "Our proprietary platform combines AI-powered design with expert human oversight. We've streamlined our process to eliminate unnecessary meetings and delays while maintaining premium quality. Most traditional agencies spend weeks on revisions—we get it right the first time.",
  },
  {
    question: "What if I need changes after delivery?",
    answer:
      "Your package includes 30 days of free minor updates. This covers text changes, image swaps, and small adjustments. For major redesigns or new features, we offer additional services at competitive rates.",
  },
  {
    question: "Do I own the website after purchase?",
    answer:
      "Absolutely! You receive full ownership of all design files, code, and assets. The first year of hosting is included, and after that you can choose to continue with us or migrate to your own hosting provider.",
  },
  {
    question: "What happens if I'm not satisfied?",
    answer:
      "We stand behind our work with a 100% satisfaction guarantee. If we don't deliver what we promised, you get a full refund within the first 7 days. No questions asked.",
  },
  {
    question: "What are the add-ons and how does pricing work?",
    answer:
      "The base package starts at $1,000 for a professional landing page. You can add extra pages ($200 each, up to 5 total), a custom domain ($150), advanced SEO ($300), blog/CMS ($250), analytics tracking ($100), or priority 24-hour delivery ($500). Pick only what you need—the configurator updates your total in real time.",
  },
  {
    question: "Can you handle e-commerce or complex features?",
    answer:
      "Yes! While our base package covers professional websites and landing pages, we can add e-commerce functionality, payment integrations, booking systems, and more. Contact us to discuss your specific needs.",
  },
  {
    question: "What do I need to provide to get started?",
    answer:
      "Just fill out our form with your business details, brand preferences, and project goals. If you have logos, images, or specific content, that's helpful—but not required. We can source professional assets if needed.",
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
