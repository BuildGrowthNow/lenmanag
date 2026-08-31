/**
 * Public side-by-side variant comparison page for client sharing.
 * URL: /compare/{leadId}
 * No auth required — designed to be shared directly with prospects/clients.
 */

import { Metadata } from "next";
import { notFound } from "next/navigation";
import { CompareClient } from "./compare-client";

interface PageProps {
  params: Promise<{ leadId: string }>;
}

type SiteVariant = {
  siteId: string;
  variantLabel: string | null;
  variantTitle: string | null;
  variantDescription: string | null;
  variantType: string;
  variantPosition: number;
  previewUrl: string;
  optionNumber: number;
  screenshotUrl: string;
};

type LeadInfo = {
  companyName: string | null;
};

async function fetchVariants(leadId: string): Promise<{ companyName: string | null; variants: SiteVariant[] }> {
  const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
  try {
    const res = await fetch(`${apiUrl}/api/v1/public/compare/${leadId}`, {
      cache: "no-store",
    });
    if (!res.ok) return { companyName: null, variants: [] };
    const envelope = await res.json();
    return { companyName: envelope.data?.companyName ?? null, variants: (envelope.data?.variants ?? []) as SiteVariant[] };
  } catch {
    return { companyName: null, variants: [] };
  }
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { leadId } = await params;
  const data = await fetchVariants(leadId);
  const name = data.companyName ?? "Site preview";
  return {
    title: `${name} — Preview variants`,
    description: `Compare all landing page variants built for ${name}.`,
  };
}

export default async function ComparePage({ params }: PageProps) {
  const { leadId } = await params;
  const publicData = await fetchVariants(leadId);
  const publishedVariants = publicData.variants;

  if (publishedVariants.length === 0) {
    notFound();
  }

  const companyName = publicData.companyName ?? "Site preview";
  return (
    <CompareClient
      variants={publishedVariants}
      companyName={companyName}
    />
  );
}
