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
  previewUrl: string;
  screenshotUrl: string;
  variantPosition: number;
  optionNumber: number;
  variantLabel: string | null;
  variantTitle: string | null;
  variantDescription: string | null;
};

export type RedesignPageData = {
  leadId: string;
  companyName: string | null;
  contactName: string | null;
  logoUrl: string | null;
  bookingUrl: string;
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
  const title = data?.companyName
    ? `${data.companyName} — Custom landing page preview`
    : "Custom landing page preview";
  return { title };
}

export default async function RedesignPage({ params }: PageProps) {
  const { slug } = await params;
  const data = await fetchRedesignData(slug);

  if (!data || data.variants.length === 0) {
    notFound();
  }

  return <RedesignClient data={data} />;
}
