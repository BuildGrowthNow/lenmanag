"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { CheckCircle2, MapPin } from "lucide-react";

interface Notification {
  id: number;
  name: string;
  location: string;
  timeAgo: string;
}

const FAKE_PURCHASES = [
  { name: "Michael Chen", location: "San Francisco, CA" },
  { name: "Sarah Johnson", location: "Austin, TX" },
  { name: "David Martinez", location: "Miami, FL" },
  { name: "Emily Wong", location: "Seattle, WA" },
  { name: "James Patterson", location: "Boston, MA" },
  { name: "Lisa Anderson", location: "Denver, CO" },
  { name: "Robert Kim", location: "Portland, OR" },
  { name: "Jessica Taylor", location: "Phoenix, AZ" },
  { name: "William Brown", location: "Chicago, IL" },
  { name: "Amanda Garcia", location: "Dallas, TX" },
  { name: "Christopher Lee", location: "Atlanta, GA" },
  { name: "Michelle Davis", location: "Nashville, TN" },
  { name: "Daniel Wilson", location: "San Diego, CA" },
  { name: "Jennifer Moore", location: "Las Vegas, NV" },
  { name: "Kevin Thomas", location: "Charlotte, NC" },
  { name: "Rachel White", location: "Minneapolis, MN" },
  { name: "Brian Jackson", location: "Detroit, MI" },
  { name: "Nicole Harris", location: "Philadelphia, PA" },
  { name: "Ryan Clark", location: "Salt Lake City, UT" },
  { name: "Stephanie Lewis", location: "Columbus, OH" },
];

const TIME_PHRASES = [
  "2 minutes ago",
  "5 minutes ago",
  "12 minutes ago",
  "23 minutes ago",
  "35 minutes ago",
  "1 hour ago",
  "2 hours ago",
  "3 hours ago",
  "5 hours ago",
  "7 hours ago",
];

export function SocialProofNotifications() {
  const [notification, setNotification] = useState<Notification | null>(null);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(max-width: 767px)");
    setIsMobile(mq.matches);
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  useEffect(() => {
    const showRandomNotification = () => {
      const randomPurchase =
        FAKE_PURCHASES[Math.floor(Math.random() * FAKE_PURCHASES.length)];
      const randomTime =
        TIME_PHRASES[Math.floor(Math.random() * TIME_PHRASES.length)];

      setNotification({
        id: Date.now(),
        name: randomPurchase.name,
        location: randomPurchase.location,
        timeAgo: randomTime,
      });

      // Hide after 5 seconds
      setTimeout(() => {
        setNotification(null);
      }, 5000);
    };

    // Show first notification after 3 seconds
    const initialTimeout = setTimeout(showRandomNotification, 3000);

    // Then show every 30-45 seconds
    const interval = setInterval(() => {
      showRandomNotification();
    }, 30000 + Math.random() * 15000);

    return () => {
      clearTimeout(initialTimeout);
      clearInterval(interval);
    };
  }, []);

  return (
    <div className={`fixed z-50 pointer-events-none ${isMobile ? "bottom-6 left-1/2 -translate-x-1/2" : "bottom-6 right-6"}`}>
      <AnimatePresence>
        {notification && (
          <motion.div
            key={notification.id}
            initial={{ opacity: 0, y: 50, scale: 0.8 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.9 }}
            transition={{
              type: "spring",
              stiffness: 500,
              damping: 30,
            }}
            className="pointer-events-auto"
          >
            <div className="bg-zinc-900 rounded-2xl shadow-2xl border-2 border-green-500 p-4 min-w-[320px] backdrop-blur-xl shadow-green-500/50">
              <div className="flex items-start gap-3">
                {/* Avatar */}
                <div className="w-12 h-12 rounded-full bg-gradient-to-br from-yellow-400 to-yellow-600 flex items-center justify-center flex-shrink-0 shadow-lg">
                  <span className="text-white font-bold text-lg">
                    {notification.name.charAt(0)}
                  </span>
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <CheckCircle2 className="w-4 h-4 text-green-500 flex-shrink-0" />
                    <span className="text-sm font-semibold text-slate-900 dark:text-white">
                      New Order
                    </span>
                  </div>
                  <p className="text-sm text-slate-700 dark:text-slate-300 mb-1">
                    <span className="font-medium">{notification.name}</span>{" "}
                    ordered a website
                  </p>
                  <div className="flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400">
                    <MapPin className="w-3 h-3" />
                    <span>{notification.location}</span>
                    <span className="mx-1">•</span>
                    <span>{notification.timeAgo}</span>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
