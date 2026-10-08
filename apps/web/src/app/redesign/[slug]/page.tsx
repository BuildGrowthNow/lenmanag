/**
 * Public client-facing redesign preview page.
 * URL: /redesign/{slug}
 * No authentication required — sent directly to clients.
 */

import { Metadata } from "next";
import { notFound } from "next/navigation";
import { RedesignClient } from "./redesign-client";

interface PageProps {
  params: Promise<{ slug: string }>;
}

export type RedesignVariant = {
  siteId: string;
  variantLabel: string;
  variantDescription: string | null;
  previewUrl: string;
  screenshotUrl: string;
  variantPosition: number;
};

export type RedesignPageData = {
  leadId: string;
  companyName: string | null;
  contactName: string | null;
  logoUrl: string | null;
  callUrl?: string;
  variants: RedesignVariant[];
};

async function fetchRedesignData(slug: string): Promise<RedesignPageData | null> {
  const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
  try {
    const res = await fetch(`${apiUrl}/api/v1/public/redesign/${slug}`, {
      cache: "no-store",
    });
    if (!res.ok) return null;
    const envelope = await res.json();
    return (envelope.data ?? null) as RedesignPageData | null;
  } catch {
    return null;
  }
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const data = await fetchRedesignData(slug);
  const companyName = data?.companyName?.trim() || "Your business";
  const title = `${companyName} website redesign preview | LenQuant`;
  const description = data
    ? `A custom website redesign prepared for ${companyName}. Preview the first concept and explore ${data.variants.length === 1 ? "the design direction" : `all ${data.variants.length} design directions`}.`
    : "Explore custom website redesign concepts created by LenQuant.";
  const siteUrl = process.env.NEXT_PUBLIC_APP_URL || "https://sites.lenquant.com";
  const pageUrl = new URL(`/redesign/${encodeURIComponent(slug)}`, siteUrl);
  const firstScreenshot = data?.variants[0]?.screenshotUrl.trim();
  const previewImageUrl = firstScreenshot || data?.logoUrl?.trim() || "/favicon.svg";
  const previewImage = new URL(previewImageUrl, siteUrl).toString();
  const imageAlt = `${companyName} website redesign preview`;

  return {
    metadataBase: new URL(siteUrl),
    title,
    description,
    alternates: { canonical: pageUrl },
    openGraph: {
      type: "website",
      url: pageUrl,
      title,
      description,
      images: [{ url: previewImage, alt: imageAlt }],
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
      images: [{ url: previewImage, alt: imageAlt }],
    },
  };
}

export default async function RedesignPage({ params }: PageProps) {
  const { slug } = await params;
  const data = await fetchRedesignData(slug);

  if (!data || data.variants.length === 0) {
    notFound();
  }

  return <RedesignClient data={data} />;
}
