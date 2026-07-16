import type { Metadata } from "next";
import { Space_Grotesk, Manrope } from "next/font/google";

import "./globals.css";

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
  title: "LenQuant Website Fabric",
  description: "Internal operator workspace for lead discovery and premium website fulfillment."
};

// Force dynamic rendering for all pages to support dynamic website generation
export const dynamic = 'force-dynamic';

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${heading.variable} ${body.variable}`} suppressHydrationWarning>
      <body style={{ fontFamily: "var(--font-body)" }} suppressHydrationWarning>
        {children}
      </body>
    </html>
  );
}
