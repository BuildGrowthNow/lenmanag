"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { approveMasterBrief, createLeadMasterBrief, refreshLeadExtraction, startLeadExtraction } from "@/lib/api/leads";
import { sendAnalyticsEvent } from "@/lib/analytics";
import { extractionAgeLabel as formatExtractionAge, formatDateTime as formatExtractionDate } from "@/lib/extraction-health";
import type { ExtractionHealth } from "@/lib/extraction-health";
import type { MasterBrief } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

type LeadBriefReviewProps = {
  leadId: string;
  brief: MasterBrief | null;
  extractionHealth: ExtractionHealth;
};

function confidenceBadgeClass(confidence: number) {
  if (confidence >= 75) return "border-emerald-500/40 bg-emerald-500/10 text-emerald-100";
  if (confidence >= 50) return "border-amber-500/40 bg-amber-500/10 text-amber-100";
  return "border-rose-500/40 bg-rose-500/10 text-rose-100";
}

function approvalBadgeClass(state: string) {
  if (state === "approved") return "border-emerald-500/40 bg-emerald-500/10 text-emerald-100";
  if (state === "pending") return "border-amber-500/40 bg-amber-500/10 text-amber-100";
  return "border-sky-500/40 bg-sky-500/10 text-sky-100";
}

function confidenceLabel(confidence: number) {
  if (confidence >= 75) return "High";
  if (confidence >= 50) return "Medium";
  return "Low";
}

const designModeLabels: Record<string, string> = {
  editorial: "Editorial",
  immersive: "Immersive",
  interactive: "Interactive",
  minimalist: "Minimalist",
  playful: "Playful",
  corporate: "Corporate",
};

export function LeadBriefReview({ leadId, brief, extractionHealth }: LeadBriefReviewProps) {
  const router = useRouter();
  const [busyAction, setBusyAction] = useState<"create" | "approve" | null>(null);
  const [extractionBusy, setExtractionBusy] = useState<"start" | "refresh" | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const { hasExtraction, blockReason, ageHours, updatedAt } = extractionHealth;
  const editingLocked = Boolean(blockReason);
  const extractionAge = formatExtractionAge(ageHours);
  const extractionUpdatedAt = formatExtractionDate(updatedAt);
  const extractionWarning = blockReason ? (
    <div className="rounded-2xl border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
      <div className="font-medium text-amber-50">{blockReason}</div>
      {extractionUpdatedAt ? (
        <div className="mt-1 text-xs text-amber-100/80">
          Last extraction: {extractionUpdatedAt}
          {extractionAge ? <span className="ml-1">({extractionAge})</span> : null}
        </div>
      ) : null}
      <div className="mt-3 flex flex-wrap gap-2">
        <Button type="button" variant="secondary" onClick={() => void handleExtractionRefresh()} disabled={extractionBusy !== null}>
          {extractionBusy
            ? extractionBusy === "refresh"
              ? "Refreshing crawl..."
              : "Starting crawl..."
            : hasExtraction
              ? "Refresh extraction"
              : "Start extraction"}
        </Button>
      </div>
    </div>
  ) : null;

  async function handleExtractionRefresh() {
    const mode: "start" | "refresh" = hasExtraction ? "refresh" : "start";
    setExtractionBusy(mode);
    setMessage(null);
    try {
      const result = mode === "refresh" ? await refreshLeadExtraction(leadId) : await startLeadExtraction(leadId);
      setMessage(`${result.job.step}. ${result.extraction.pagesCrawled} page(s) crawled.`);
      void sendAnalyticsEvent({
        leadId,
        eventType: "admin_action",
        eventName: mode === "refresh" ? "Extraction refresh triggered from brief" : "Extraction started from brief",
        metadata: { scope: "brief_editor", action: mode }
      });
      router.refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Failed to trigger extraction.");
    } finally {
      setExtractionBusy(null);
    }
  }

  async function handleCreateBrief() {
    if (editingLocked) {
      return;
    }
    setBusyAction("create");
    setMessage(null);
    try {
      await createLeadMasterBrief(leadId);
      setMessage("Master brief generated from the latest extraction snapshot.");
      void sendAnalyticsEvent({
        leadId,
        eventType: "brief_edited",
        eventName: "Master brief generated",
        metadata: { scope: "brief_editor" }
      });
      router.refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not create the brief.");
    } finally {
      setBusyAction(null);
    }
  }

  async function handleApprove() {
    if (!brief || editingLocked) {
      return;
    }
    setBusyAction("approve");
    setMessage(null);
    try {
      await approveMasterBrief(leadId, brief.reviewNotes ?? undefined);
      setMessage("Master brief approved. Site generation will start automatically.");
      void sendAnalyticsEvent({
        leadId,
        eventType: "brief_approved",
        eventName: "Master brief approved",
        metadata: { scope: "brief_editor" }
      });
      router.refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not approve the brief.");
    } finally {
      setBusyAction(null);
    }
  }

  if (!brief) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Site brief</CardTitle>
          <CardDescription>The brief is created from the latest extraction snapshot and used to generate your landing page.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {extractionWarning}
          <div className="rounded-2xl border border-line bg-panel-2 p-4 text-sm text-text">
            <div className="text-xs uppercase tracking-[0.18em] text-muted">Status</div>
            <div className="mt-2">
              {hasExtraction
                ? "No brief has been generated yet. Create one from the latest extraction snapshot to proceed."
                : "Run a crawl first. The brief cannot be generated until there is extraction data."}
            </div>
          </div>
          <div className="flex flex-wrap gap-3">
            <Button type="button" onClick={() => void handleCreateBrief()} disabled={!hasExtraction || busyAction === "create" || editingLocked}>
              {busyAction === "create" ? "Generating..." : "Create master brief"}
            </Button>
          </div>
          {message ? <div className="text-xs leading-5 text-muted">{message}</div> : null}
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
          <div>
            <CardTitle>Master brief review</CardTitle>
            <CardDescription>AI-generated brief for your landing page strategy. Approve to proceed to site generation.</CardDescription>
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge className={approvalBadgeClass(brief.approvalState)}>{brief.approvalState.replace(/_/g, " ")}</Badge>
            <Badge>v{brief.version}</Badge>
            <Badge className={confidenceBadgeClass(brief.confidenceScore)}>{confidenceLabel(brief.confidenceScore)} confidence</Badge>
            {brief.designMode && designModeLabels[brief.designMode] && (
              <Badge className="border-violet-500/40 bg-violet-500/10 text-violet-100">{designModeLabels[brief.designMode]}</Badge>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-5">
        {extractionWarning}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          <div className="rounded-2xl border border-line bg-panel-2 p-4">
            <div className="text-xs uppercase tracking-[0.18em] text-muted">Business Goal</div>
            <div className="mt-2 text-sm text-text">{brief.businessGoal}</div>
          </div>
          <div className="rounded-2xl border border-line bg-panel-2 p-4">
            <div className="text-xs uppercase tracking-[0.18em] text-muted">Primary Audience</div>
            <div className="mt-2 text-sm text-text">{brief.primaryAudience}</div>
          </div>
          <div className="rounded-2xl border border-line bg-panel-2 p-4">
            <div className="text-xs uppercase tracking-[0.18em] text-muted">Conversion Action</div>
            <div className="mt-2 text-sm text-text">{brief.conversionAction}</div>
          </div>
          <div className="rounded-2xl border border-line bg-panel-2 p-4">
            <div className="text-xs uppercase tracking-[0.18em] text-muted">Value Proposition</div>
            <div className="mt-2 text-sm text-text">{brief.valueProposition}</div>
          </div>
          <div className="rounded-2xl border border-line bg-panel-2 p-4">
            <div className="text-xs uppercase tracking-[0.18em] text-muted">Tone & Voice</div>
            <div className="mt-2 text-sm text-text">{brief.toneAndVoice}</div>
          </div>
          <div className="rounded-2xl border border-line bg-panel-2 p-4">
            <div className="text-xs uppercase tracking-[0.18em] text-muted">Visual Style</div>
            <div className="mt-2 text-sm text-text">{brief.visualStyle}</div>
          </div>
        </div>

        <div className="rounded-2xl border border-line bg-panel-2 p-4">
          <div className="text-xs uppercase tracking-[0.18em] text-muted">Hero Headline</div>
          <div className="mt-2 text-lg font-semibold text-text">{brief.headline}</div>
          <div className="mt-1 text-sm text-muted">{brief.subheadline}</div>
        </div>

        {brief.sections && brief.sections.length > 0 && (
          <div className="space-y-3">
            <div className="text-xs uppercase tracking-[0.18em] text-muted font-semibold">Page Sections</div>
            <div className="grid gap-3 md:grid-cols-2">
              {brief.sections.map((section, index) => (
                <div key={index} className="rounded-2xl border border-line bg-panel-2 p-4">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="text-xs uppercase tracking-[0.18em] text-muted">{section.purpose}</div>
                      <div className="mt-1 font-semibold text-text">{section.headline}</div>
                    </div>
                  </div>
                  <div className="mt-2 text-sm text-text">{section.contentSummary}</div>
                  {section.contentPoints && section.contentPoints.length > 0 && (
                    <div className="mt-2 space-y-1">
                      {section.contentPoints.map((point, pIndex) => (
                        <div key={pIndex} className="text-sm text-muted flex gap-2">
                          <span className="text-xs">•</span>
                          <span>{point}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {brief.creativeDirection && (
          <div className="space-y-3">
            <div className="text-xs uppercase tracking-[0.18em] text-muted font-semibold">Creative Direction</div>
            <div className="grid gap-3 md:grid-cols-2">
              <div className="rounded-2xl border border-line bg-panel-2 p-4">
                <div className="text-xs uppercase tracking-[0.18em] text-muted">Design Concept</div>
                <div className="mt-2 text-sm text-text">{brief.creativeDirection.designConcept}</div>
              </div>
              <div className="rounded-2xl border border-line bg-panel-2 p-4">
                <div className="text-xs uppercase tracking-[0.18em] text-muted">Hero Treatment</div>
                <div className="mt-2 text-sm text-text">{brief.creativeDirection.heroTreatment}</div>
              </div>
              <div className="rounded-2xl border border-line bg-panel-2 p-4">
                <div className="text-xs uppercase tracking-[0.18em] text-muted">Signature Technique</div>
                <div className="mt-2 text-sm font-medium text-text">{brief.creativeDirection.signatureTechnique}</div>
              </div>
              <div className="rounded-2xl border border-line bg-panel-2 p-4">
                <div className="text-xs uppercase tracking-[0.18em] text-muted">Layout Strategy</div>
                <div className="mt-2 text-sm text-text">{brief.creativeDirection.layoutStrategy}</div>
              </div>
              {brief.creativeDirection.microInteractions.length > 0 && (
                <div className="rounded-2xl border border-line bg-panel-2 p-4 md:col-span-2">
                  <div className="text-xs uppercase tracking-[0.18em] text-muted">Micro-interactions</div>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {brief.creativeDirection.microInteractions.map((interaction, i) => (
                      <span key={i} className="text-xs px-2 py-1 bg-panel-3 rounded-full text-text">{interaction}</span>
                    ))}
                  </div>
                </div>
              )}
              {brief.creativeDirection.inspirationKeywords.length > 0 && (
                <div className="rounded-2xl border border-line bg-panel-2 p-4 md:col-span-2">
                  <div className="text-xs uppercase tracking-[0.18em] text-muted">Inspiration Keywords</div>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {brief.creativeDirection.inspirationKeywords.map((keyword, i) => (
                      <span key={i} className="text-xs px-2 py-1 bg-blue-500/20 text-blue-300 rounded-full">{keyword}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        <div className="rounded-2xl border border-line bg-panel-2 p-4">
          <div className="text-xs uppercase tracking-[0.18em] text-muted">CTA Strategy</div>
          <div className="mt-2 text-sm text-text">{brief.ctaStrategy}</div>
        </div>

        <div className="flex flex-wrap gap-3">
          <Button type="button" onClick={() => void handleApprove()} disabled={busyAction === "approve" || editingLocked || brief.approvalState === "approved"}>
            {busyAction === "approve" ? "Approving..." : brief.approvalState === "approved" ? "Already approved" : "Approve & generate site"}
          </Button>
        </div>
        {message ? <div className="text-xs leading-5 text-muted">{message}</div> : null}
      </CardContent>
    </Card>
  );
}
