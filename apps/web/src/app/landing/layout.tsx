import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Professional Websites in 3 Days | Lenquant",
  description: "Get your professional website delivered in just 3 days. Custom design, premium tech, SEO optimized. No meetings, no hassle. $1,000 limited-time offer.",
  keywords: [
    "website design",
    "web development",
    "fast website",
    "3 day website",
    "custom website",
    "professional website",
    "website builder",
    "landing page",
    "SEO optimized",
  ],
  authors: [{ name: "Lenquant" }],
  openGraph: {
    title: "Professional Websites in 3 Days | Lenquant",
    description: "Custom websites delivered at lightning speed. Premium design, hosting included.",
    type: "website",
    siteName: "Lenquant",
  },
  twitter: {
    card: "summary_large_image",
    title: "Professional Websites in 3 Days | Lenquant",
    description: "Custom websites delivered at lightning speed. Premium design, hosting included.",
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function LandingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
