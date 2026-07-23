import type { Metadata } from "next";
import { Space_Grotesk, Manrope } from "next/font/google";

import "./globals.css";
import { CursorGlow } from "@/components/cursor-glow";

const heading = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-heading",
  display: "swap",
});

const body = Manrope({
  subsets: ["latin"],
  variable: "--font-body",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Master Design - Premium Websites in 3 Days | Lenquant",
  description: "Premium, custom-crafted websites delivered in 3 days for just $1,000. Master design, fast delivery, no compromises. Get your masterpiece today.",
  icons: {
    icon: "/favicon.svg",
  },
  keywords: "website design, web development, custom website, fast delivery, professional website, landing page, masterpiece",
  openGraph: {
    title: "Master Design - Premium Websites in 3 Days | Lenquant",
    description: "Premium, custom-crafted websites delivered in 3 days for just $1,000. Master design, fast delivery, no compromises.",
    type: "website",
    url: "https://sites.lenquant.com",
    images: [
      {
        url: "/og-image.png",
        width: 1200,
        height: 630,
        alt: "Lenquant - Master Design Premium Websites",
      },
    ],
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-snippet": -1,
      "max-image-preview": "large",
      "max-video-preview": -1,
    },
  },
};

// Force dynamic rendering for all pages to support dynamic website generation
export const dynamic = 'force-dynamic';

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${heading.variable} ${body.variable}`} suppressHydrationWarning>
      <body style={{ fontFamily: "var(--font-body)" }} suppressHydrationWarning>
        <CursorGlow />
        {children}
      </body>
    </html>
  );
}
