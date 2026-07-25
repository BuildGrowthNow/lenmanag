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
  id: string;
  leadId: string;
  variantLabel: string;
  variantType: string;
  variantPosition: number;
  previewSlug: string;
  previewUrl: string;
  compiledBundleUrl: string | null;
  staticHtml: string | null;
  compilationStatus: string;
  readinessStatus: string;
  qualityScore: number;
};

type LeadInfo = {
  companyName: string | null;
  websiteUrl: string;
  industry: string | null;
};

async function fetchVariants(leadId: string): Promise<SiteVariant[]> {
  const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
  try {
    const res = await fetch(`${apiUrl}/api/v1/sites/variants/${leadId}`, {
      cache: "no-store",
    });
    if (!res.ok) return [];
    const envelope = await res.json();
    return (envelope.data ?? []) as SiteVariant[];
  } catch {
    return [];
  }
}

async function fetchLead(leadId: string): Promise<LeadInfo | null> {
  const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
  try {
    const res = await fetch(`${apiUrl}/api/v1/leads/${leadId}`, {
      cache: "no-store",
    });
    if (!res.ok) return null;
    const envelope = await res.json();
    return envelope.data ?? null;
  } catch {
    return null;
  }
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { leadId } = await params;
  const lead = await fetchLead(leadId);
  const name = lead?.companyName ?? "Site preview";
  return {
    title: `${name} — Preview variants`,
    description: `Compare all landing page variants built for ${name}.`,
  };
}

export default async function ComparePage({ params }: PageProps) {
  const { leadId } = await params;
  const [variants, lead] = await Promise.all([
    fetchVariants(leadId),
    fetchLead(leadId),
  ]);

  const publishedVariants = variants.filter(
    (v) =>
      v.compilationStatus === "success" &&
      v.readinessStatus !== "blocked" &&
      (v.compiledBundleUrl || v.staticHtml)
  );

  if (publishedVariants.length === 0) {
    notFound();
  }

  const companyName = lead?.companyName ?? "Your site preview";
  const appUrl = process.env.NEXT_PUBLIC_APP_URL || "https://sites.lenquant.com";

  return (
    <CompareClient
      variants={publishedVariants}
      companyName={companyName}
      leadId={leadId}
      appUrl={appUrl}
    />
  );
}
