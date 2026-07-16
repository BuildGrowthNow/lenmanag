"use client";

import { motion } from "framer-motion";
import { Mail, Phone, MapPin } from "lucide-react";

export function Footer() {
  const currentYear = new Date().getFullYear();

  const handleSmoothScroll = (sectionId: string) => {
    const element = document.getElementById(sectionId);
    if (element) {
      element.scrollIntoView({ behavior: "smooth" });
    }
  };

  return (
    <footer className="relative px-6 py-16 bg-slate-950/50 border-t border-white/10">
      <div className="max-w-7xl mx-auto">
        {/* Footer Content Grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-12 mb-12">
          {/* Company Info */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            viewport={{ once: true }}
          >
            <div className="mb-4">
              <h3 className="text-2xl font-bold text-white mb-2">Lenquant</h3>
              <p className="text-slate-400 text-sm">
                Premium websites delivered in 3 days. Professional design, reliable hosting, and dedicated support.
              </p>
            </div>
            <div className="space-y-2">
              <a
                href="https://lenquant.com"
                target="_blank"
                rel="noopener noreferrer"
                className="text-yellow-500 hover:text-yellow-400 transition-colors text-sm"
              >
                Visit lenquant.com →
              </a>
            </div>
          </motion.div>

          {/* Quick Links */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1, duration: 0.5 }}
            viewport={{ once: true }}
          >
            <h4 className="text-white font-semibold mb-6">Quick Links</h4>
            <ul className="space-y-3">
              <li>
                <button
                  onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
                  className="text-slate-300 hover:text-yellow-500 transition-colors text-sm"
                >
                  Home
                </button>
              </li>
              <li>
                <button
                  onClick={() => handleSmoothScroll("features")}
                  className="text-slate-300 hover:text-yellow-500 transition-colors text-sm"
                >
                  Services
                </button>
              </li>
              <li>
                <button
                  onClick={() => handleSmoothScroll("pricing")}
                  className="text-slate-300 hover:text-yellow-500 transition-colors text-sm"
                >
                  Pricing
                </button>
              </li>
              <li>
                <a
                  href="mailto:contact@lenquant.com"
                  className="text-slate-300 hover:text-yellow-500 transition-colors text-sm"
                >
                  Contact
                </a>
              </li>
            </ul>
          </motion.div>

          {/* Legal */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2, duration: 0.5 }}
            viewport={{ once: true }}
          >
            <h4 className="text-white font-semibold mb-6">Legal</h4>
            <ul className="space-y-3">
              <li>
                <a
                  href="/privacy"
                  className="text-slate-300 hover:text-yellow-500 transition-colors text-sm"
                >
                  Privacy Policy
                </a>
              </li>
              <li>
                <a
                  href="/terms"
                  className="text-slate-300 hover:text-yellow-500 transition-colors text-sm"
                >
                  Terms of Service
                </a>
              </li>
            </ul>
          </motion.div>

          {/* Contact Info */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3, duration: 0.5 }}
            viewport={{ once: true }}
          >
            <h4 className="text-white font-semibold mb-6">Contact</h4>
            <ul className="space-y-4">
              <li className="flex items-start gap-3">
                <Mail className="w-5 h-5 text-yellow-500 flex-shrink-0 mt-0.5" />
                <a
                  href="mailto:contact@lenquant.com"
                  className="text-slate-300 hover:text-yellow-500 transition-colors text-sm"
                >
                  contact@lenquant.com
                </a>
              </li>
              <li className="flex items-start gap-3">
                <Phone className="w-5 h-5 text-yellow-500 flex-shrink-0 mt-0.5" />
                <a
                  href="tel:+18457211974"
                  className="text-slate-300 hover:text-yellow-500 transition-colors text-sm"
                >
                  +1 (845) 721-1974
                </a>
              </li>
              <li className="flex items-start gap-3">
                <MapPin className="w-5 h-5 text-yellow-500 flex-shrink-0 mt-0.5" />
                <address className="text-slate-300 text-sm not-italic">
                  510 South Main Street
                  <br />
                  South Bend, IN 46601
                </address>
              </li>
            </ul>
          </motion.div>
        </div>

        {/* Divider */}
        <div className="border-t border-white/10 mb-8" />

        {/* Bottom Section */}
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          transition={{ duration: 0.5 }}
          viewport={{ once: true }}
          className="text-center"
        >
          <p className="text-slate-400 text-sm">
            &copy; {currentYear} Lenquant. All rights reserved.
          </p>
        </motion.div>
      </div>
    </footer>
  );
}
