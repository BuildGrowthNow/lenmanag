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
  { name: "Nathan Rivera", location: "San Francisco, CA" },
  { name: "Chloe Bennett", location: "Austin, TX" },
  { name: "Ethan Murphy", location: "Miami, FL" },
  { name: "Grace Nguyen", location: "Seattle, WA" },
  { name: "Owen Fletcher", location: "Boston, MA" },
  { name: "Isla Chambers", location: "Denver, CO" },
  { name: "Caleb Warren", location: "Portland, OR" },
  { name: "Zoe Harrington", location: "Phoenix, AZ" },
  { name: "Miles Donovan", location: "Chicago, IL" },
  { name: "Ava Sinclair", location: "Dallas, TX" },
  { name: "Liam Fitzgerald", location: "Atlanta, GA" },
  { name: "Nora Callahan", location: "Nashville, TN" },
  { name: "Finn Whitfield", location: "San Diego, CA" },
  { name: "Ellie Stratton", location: "Las Vegas, NV" },
  { name: "Leo Padilla", location: "Charlotte, NC" },
  { name: "Hazel Tran", location: "Minneapolis, MN" },
  { name: "Jonah Mercer", location: "Detroit, MI" },
  { name: "Scarlett Odom", location: "Philadelphia, PA" },
  { name: "Cole Espinoza", location: "Salt Lake City, UT" },
  { name: "Piper Vance", location: "Columbus, OH" },
];

const TIME_PHRASES = [
  "yesterday",
  "2 days ago",
  "3 days ago",
  "4 days ago",
  "5 days ago",
  "last week",
  "about a week ago",
  "2 weeks ago",
  "3 weeks ago",
  "this month",
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
            <div className="bg-zinc-900 rounded-2xl shadow-md border-2 border-yellow-500 p-4 min-w-[320px] backdrop-blur-xl shadow-yellow-500/20 opacity-90">
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
