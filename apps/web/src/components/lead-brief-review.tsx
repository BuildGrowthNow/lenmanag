"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";

import { approveLeadBrief, createLeadBrief, refreshLeadExtraction, startLeadExtraction, updateLeadBrief } from "@/lib/api/leads";
import { sendAnalyticsEvent } from "@/lib/analytics";
import { extractionAgeLabel as formatExtractionAge, formatDateTime as formatExtractionDate } from "@/lib/extraction-health";
import type { ExtractionHealth } from "@/lib/extraction-health";
import type { SiteBrief } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";

type LeadBriefReviewProps = {
  leadId: string;
  brief: SiteBrief | null;
  extractionHealth: ExtractionHealth;
};

type BriefFormState = {
  companySummary: string;
  valuePropositionSummary: string;
  audienceHypothesis: string;
  toneProfile: string;
  conversionAngle: string;
  recommendedHero: string;
  recommendedSections: string;
  reviewNotes: string;
};

function confidenceBadgeClass(confidence: number) {
  if (confidence >= 75) return "border-emerald-500/40 bg-emerald-500/10 text-emerald-100";
  if (confidence >= 50) return "border-amber-500/40 bg-amber-500/10 text-amber-100";
  return "border-rose-500/40 bg-rose-500/10 text-rose-100";
}

function approvalBadgeClass(state: string) {
  if (state === "approved") return "border-emerald-500/40 bg-emerald-500/10 text-emerald-100";
  if (state === "needs_review") return "border-amber-500/40 bg-amber-500/10 text-amber-100";
  return "border-sky-500/40 bg-sky-500/10 text-sky-100";
}

function sourceBadgeClass(kind: string) {
  if (kind === "source_backed") return "border-emerald-500/40 bg-emerald-500/10 text-emerald-100";
  return "border-sky-500/40 bg-sky-500/10 text-sky-100";
}

function briefToForm(brief: SiteBrief | null): BriefFormState {
  return {
    companySummary: brief?.companySummary.value ?? "",
    valuePropositionSummary: brief?.valuePropositionSummary.value ?? "",
    audienceHypothesis: brief?.audienceHypothesis.value ?? "",
    toneProfile: brief?.toneProfile.value ?? "",
    conversionAngle: brief?.conversionAngle.value ?? "",
    recommendedHero: brief?.recommendedHero.value ?? "",
    recommendedSections: brief?.recommendedSections.map((section) => section.title).join("\n") ?? "",
    reviewNotes: brief?.reviewNotes ?? ""
  };
}

function normalizeLines(value: string) {
  return value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

function confidenceLabel(confidence: number) {
  if (confidence >= 75) return "High";
  if (confidence >= 50) return "Medium";
  return "Low";
}

export function LeadBriefReview({ leadId, brief, extractionHealth }: LeadBriefReviewProps) {
  const router = useRouter();
  const [form, setForm] = useState<BriefFormState>(() => briefToForm(brief));
  const [busyAction, setBusyAction] = useState<"create" | "save" | "approve" | null>(null);
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

  useEffect(() => {
    setForm(briefToForm(brief));
    setMessage(null);
  }, [brief]);

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
      await createLeadBrief(leadId);
      setMessage("Brief generated from the latest extraction snapshot.");
      void sendAnalyticsEvent({
        leadId,
        eventType: "brief_edited",
        eventName: "Brief generated from editor",
        metadata: { scope: "brief_editor" }
      });
      router.refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not create the brief.");
    } finally {
      setBusyAction(null);
    }
  }

  async function handleSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (editingLocked || !brief) {
      return;
    }
    setBusyAction("save");
    setMessage(null);
    try {
      await updateLeadBrief(leadId, {
        companySummary: form.companySummary,
        valuePropositionSummary: form.valuePropositionSummary,
        audienceHypothesis: form.audienceHypothesis,
        toneProfile: form.toneProfile,
        conversionAngle: form.conversionAngle,
        recommendedHero: form.recommendedHero,
        recommendedSections: normalizeLines(form.recommendedSections),
        reviewNotes: form.reviewNotes
      });
      setMessage("Brief saved as a new version.");
      void sendAnalyticsEvent({
        leadId,
        eventType: "brief_edited",
        eventName: "Brief saved from editor",
        metadata: { scope: "brief_editor" }
      });
      router.refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not save the brief.");
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
      await approveLeadBrief(leadId);
      setMessage("Brief approved.");
      void sendAnalyticsEvent({
        leadId,
        eventType: "brief_approved",
        eventName: "Brief approved from editor",
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
          <CardDescription>The brief is created from the latest extraction snapshot and stays versioned after every edit.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {extractionWarning}
          <div className="rounded-2xl border border-line bg-panel-2 p-4 text-sm text-text">
            <div className="text-xs uppercase tracking-[0.18em] text-muted">Status</div>
            <div className="mt-2">
              {hasExtraction
                ? "No brief has been generated yet. Create one from the latest extraction snapshot to start the review loop."
                : "Run a crawl first. The brief cannot be generated until there is extraction data to interpret."}
            </div>
          </div>
          <div className="flex flex-wrap gap-3">
            <Button type="button" onClick={() => void handleCreateBrief()} disabled={!hasExtraction || busyAction === "create" || editingLocked}>
              {busyAction === "create" ? "Generating..." : "Create brief from extraction"}
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
            <CardTitle>Site brief review</CardTitle>
            <CardDescription>Operators can edit the interpreted brief while citations remain locked to the source crawl and asset references.</CardDescription>
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge className={approvalBadgeClass(brief.approvalState)}>{brief.approvalState.replace("_", " ")}</Badge>
            <Badge>v{brief.version}</Badge>
            <Badge className={confidenceBadgeClass(brief.confidenceScore)}>{confidenceLabel(brief.confidenceScore)} confidence</Badge>
            {editingLocked ? <Badge className="border-amber-500/40 bg-amber-500/10 text-amber-100">Editing locked</Badge> : null}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-5">
        {extractionWarning}
        <div className="grid gap-3 md:grid-cols-3">
          <div className="rounded-2xl border border-line bg-panel-2 p-4 text-xs text-muted">
            <div className="uppercase tracking-[0.18em]">Source extraction</div>
            <div className="mt-2 text-sm text-text">Version {brief.sourceExtractionVersion}</div>
            <div className="mt-1 break-all">ID: {brief.sourceExtractionId}</div>
          </div>
          <div className="rounded-2xl border border-line bg-panel-2 p-4 text-xs text-muted">
            <div className="uppercase tracking-[0.18em]">Approval state</div>
            <div className="mt-2 text-sm text-text">{brief.approvalState}</div>
            <div className="mt-1">{brief.needsReview ? "This brief still needs operator review before generation begins." : "This brief is approved for the next phase."}</div>
          </div>
          <div className="rounded-2xl border border-line bg-panel-2 p-4 text-xs text-muted">
            <div className="uppercase tracking-[0.18em]">Review notes</div>
            <div className="mt-2 text-sm text-text">{brief.reviewNotes || "No review notes recorded."}</div>
          </div>
        </div>

        <form className="grid gap-4 xl:grid-cols-[1.05fr_0.95fr]" onSubmit={(event) => void handleSave(event)}>
          <div className="space-y-4">
            <div className="rounded-2xl border border-line bg-panel-2 p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <div className="text-xs uppercase tracking-[0.18em] text-muted">Company summary</div>
                  <div className="mt-1 text-xs text-muted">
                    <span className="mr-2">Source label:</span>
                    <Badge className={sourceBadgeClass(brief.companySummary.evidence.sourceKind)}>{brief.companySummary.evidence.sourceKind.replace("_", " ")}</Badge>
                    <Badge className="ml-2">{brief.companySummary.evidence.inferenceLabel}</Badge>
                    <Badge className={`ml-2 ${confidenceBadgeClass(brief.companySummary.evidence.confidence)}`}>{brief.companySummary.evidence.confidence}%</Badge>
                  </div>
                </div>
              </div>
              <Textarea
                className="mt-3"
                value={form.companySummary}
                onChange={(event) => setForm((current) => ({ ...current, companySummary: event.target.value }))}
                rows={4}
                disabled={editingLocked}
              />
            </div>

            <div className="rounded-2xl border border-line bg-panel-2 p-4">
              <div className="text-xs uppercase tracking-[0.18em] text-muted">Value proposition summary</div>
              <div className="mt-1 text-xs text-muted">
                <Badge className={sourceBadgeClass(brief.valuePropositionSummary.evidence.sourceKind)}>{brief.valuePropositionSummary.evidence.sourceKind.replace("_", " ")}</Badge>
                <Badge className="ml-2">{brief.valuePropositionSummary.evidence.inferenceLabel}</Badge>
                <Badge className={`ml-2 ${confidenceBadgeClass(brief.valuePropositionSummary.evidence.confidence)}`}>{brief.valuePropositionSummary.evidence.confidence}%</Badge>
              </div>
              <Textarea
                className="mt-3"
                value={form.valuePropositionSummary}
                onChange={(event) => setForm((current) => ({ ...current, valuePropositionSummary: event.target.value }))}
                rows={3}
                disabled={editingLocked}
              />
            </div>

            <div className="rounded-2xl border border-line bg-panel-2 p-4">
              <div className="text-xs uppercase tracking-[0.18em] text-muted">Audience hypothesis</div>
              <div className="mt-1 text-xs text-muted">
                <Badge className={sourceBadgeClass(brief.audienceHypothesis.evidence.sourceKind)}>{brief.audienceHypothesis.evidence.sourceKind.replace("_", " ")}</Badge>
                <Badge className="ml-2">{brief.audienceHypothesis.evidence.inferenceLabel}</Badge>
                <Badge className={`ml-2 ${confidenceBadgeClass(brief.audienceHypothesis.evidence.confidence)}`}>{brief.audienceHypothesis.evidence.confidence}%</Badge>
              </div>
              <Textarea
                className="mt-3"
                value={form.audienceHypothesis}
                onChange={(event) => setForm((current) => ({ ...current, audienceHypothesis: event.target.value }))}
                rows={3}
                disabled={editingLocked}
              />
            </div>

            <div className="rounded-2xl border border-line bg-panel-2 p-4">
              <div className="text-xs uppercase tracking-[0.18em] text-muted">Tone profile</div>
              <div className="mt-1 text-xs text-muted">
                <Badge className={sourceBadgeClass(brief.toneProfile.evidence.sourceKind)}>{brief.toneProfile.evidence.sourceKind.replace("_", " ")}</Badge>
                <Badge className="ml-2">{brief.toneProfile.evidence.inferenceLabel}</Badge>
                <Badge className={`ml-2 ${confidenceBadgeClass(brief.toneProfile.evidence.confidence)}`}>{brief.toneProfile.evidence.confidence}%</Badge>
              </div>
              <Textarea
                className="mt-3"
                value={form.toneProfile}
                onChange={(event) => setForm((current) => ({ ...current, toneProfile: event.target.value }))}
                rows={3}
                disabled={editingLocked}
              />
            </div>

            <div className="rounded-2xl border border-line bg-panel-2 p-4">
              <div className="text-xs uppercase tracking-[0.18em] text-muted">Conversion angle</div>
              <div className="mt-1 text-xs text-muted">
                <Badge className={sourceBadgeClass(brief.conversionAngle.evidence.sourceKind)}>{brief.conversionAngle.evidence.sourceKind.replace("_", " ")}</Badge>
                <Badge className="ml-2">{brief.conversionAngle.evidence.inferenceLabel}</Badge>
                <Badge className={`ml-2 ${confidenceBadgeClass(brief.conversionAngle.evidence.confidence)}`}>{brief.conversionAngle.evidence.confidence}%</Badge>
              </div>
              <Textarea
                className="mt-3"
                value={form.conversionAngle}
                onChange={(event) => setForm((current) => ({ ...current, conversionAngle: event.target.value }))}
                rows={3}
                disabled={editingLocked}
              />
            </div>

            <div className="rounded-2xl border border-line bg-panel-2 p-4">
              <div className="text-xs uppercase tracking-[0.18em] text-muted">Hero direction</div>
              <div className="mt-1 text-xs text-muted">
                <Badge className={sourceBadgeClass(brief.recommendedHero.evidence.sourceKind)}>{brief.recommendedHero.evidence.sourceKind.replace("_", " ")}</Badge>
                <Badge className="ml-2">{brief.recommendedHero.evidence.inferenceLabel}</Badge>
                <Badge className={`ml-2 ${confidenceBadgeClass(brief.recommendedHero.evidence.confidence)}`}>{brief.recommendedHero.evidence.confidence}%</Badge>
              </div>
              <Textarea
                className="mt-3"
                value={form.recommendedHero}
                onChange={(event) => setForm((current) => ({ ...current, recommendedHero: event.target.value }))}
                rows={3}
                disabled={editingLocked}
              />
            </div>

            <div className="rounded-2xl border border-line bg-panel-2 p-4">
              <div className="text-xs uppercase tracking-[0.18em] text-muted">Recommended sections</div>
              <div className="mt-1 text-xs text-muted">
                <span>One section title per line. Source citations remain locked even if the operator changes this list.</span>
              </div>
              <Textarea
                className="mt-3"
                value={form.recommendedSections}
                onChange={(event) => setForm((current) => ({ ...current, recommendedSections: event.target.value }))}
                rows={4}
                disabled={editingLocked}
              />
            </div>

            <div className="rounded-2xl border border-line bg-panel-2 p-4">
              <div className="text-xs uppercase tracking-[0.18em] text-muted">Review notes</div>
              <Textarea
                className="mt-3"
                value={form.reviewNotes}
                onChange={(event) => setForm((current) => ({ ...current, reviewNotes: event.target.value }))}
                rows={3}
                disabled={editingLocked}
              />
            </div>

            <div className="flex flex-wrap gap-3">
              <Button type="submit" disabled={busyAction === "save" || editingLocked}>
                {busyAction === "save" ? "Saving..." : "Save new version"}
              </Button>
              <Button type="button" variant="secondary" onClick={() => void handleApprove()} disabled={busyAction === "approve" || editingLocked}>
                {busyAction === "approve" ? "Approving..." : "Approve brief"}
              </Button>
            </div>
            {message ? <div className="text-xs leading-5 text-muted">{message}</div> : null}
          </div>

          <div className="space-y-4">
            {brief.visualRedesign && brief.visualRedesign.length > 0 && (
              <div className="rounded-2xl border border-line bg-panel-2 p-4">
                <div className="text-xs uppercase tracking-[0.18em] text-muted">Visual Redesign Cues</div>
                <div className="mt-3 space-y-4">
                  {brief.visualRedesign.map((page, pageIndex) => (
                    <div key={pageIndex} className="space-y-2">
                      <div className="text-sm font-medium">Page: {page.pageUrl}</div>
                      <Badge className="bg-primary/10 text-primary hover:bg-primary/20">Art Direction: {page.artDirection}</Badge>
                      <div className="mt-2 space-y-2 pl-4 border-l-2 border-line">
                        {page.critiques.map((critique, cIndex) => (
                          <div key={cIndex} className="rounded-xl border border-line bg-panel px-3 py-2">
                            <div className="flex flex-wrap items-center gap-2">
                              <Badge>{critique.sectionType}</Badge>
                              <Badge className={confidenceBadgeClass(critique.confidence)}>{critique.confidence}%</Badge>
                              <span className="text-sm text-text">Recommended Component: <span className="font-semibold">{critique.recommendedComponent}</span></span>
                            </div>
                            <div className="mt-2 space-y-1">
                              {critique.redesignGoal && (
                                <div className="text-sm text-text"><span className="text-muted text-xs uppercase mr-1">Goal:</span> {critique.redesignGoal}</div>
                              )}
                              {critique.contentToReuse.length > 0 && (
                                <div className="text-sm text-text"><span className="text-muted text-xs uppercase mr-1">Reuse:</span> {critique.contentToReuse.join(", ")}</div>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="rounded-2xl border border-line bg-panel-2 p-4">
              <div className="text-xs uppercase tracking-[0.18em] text-muted">Source citations</div>
              <div className="mt-3 space-y-2">
                {brief.sourceCitations.length ? (
                  brief.sourceCitations.map((citation, index) => (
                    <div key={`${citation.kind}-${citation.sourceUrl}-${index}`} className="rounded-xl border border-line bg-panel px-3 py-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge>{citation.kind}</Badge>
                        {citation.evidenceType ? <Badge>{citation.evidenceType}</Badge> : null}
                        {citation.assetType ? <Badge>{citation.assetType}</Badge> : null}
                        <Badge className={confidenceBadgeClass(citation.confidence)}>{citation.confidence}%</Badge>
                        <span className="text-sm text-text">{citation.label}</span>
                      </div>
                      <div className="mt-2 break-all text-xs text-muted">{citation.sourceUrl}</div>
                      <div className="mt-1 text-sm text-text">{citation.excerpt}</div>
                    </div>
                  ))
                ) : (
                  <div className="text-sm text-muted">No citations were stored with this brief.</div>
                )}
              </div>
            </div>

            <div className="rounded-2xl border border-line bg-panel-2 p-4">
              <div className="text-xs uppercase tracking-[0.18em] text-muted">Brand asset provenance</div>
              <div className="mt-3 space-y-2">
                {brief.brandAssetProvenance.length ? (
                  brief.brandAssetProvenance.map((reference, index) => (
                    <div key={`${reference.kind}-${reference.sourceUrl}-${index}`} className="rounded-xl border border-line bg-panel px-3 py-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge>{reference.kind}</Badge>
                        {reference.assetType ? <Badge>{reference.assetType}</Badge> : null}
                        <Badge className={confidenceBadgeClass(reference.confidence)}>{reference.confidence}%</Badge>
                        <span className="text-sm text-text">{reference.label}</span>
                      </div>
                      <div className="mt-2 break-all text-xs text-muted">{reference.sourceUrl}</div>
                      <div className="mt-1 text-sm text-text">{reference.excerpt}</div>
                    </div>
                  ))
                ) : (
                  <div className="text-sm text-muted">No public brand assets were captured with this brief.</div>
                )}
              </div>
            </div>

            <div className="rounded-2xl border border-line bg-panel-2 p-4">
              <div className="text-xs uppercase tracking-[0.18em] text-muted">Proof points</div>
              <div className="mt-3 space-y-2">
                {brief.proofPoints.length ? (
                  brief.proofPoints.map((proof, index) => (
                    <div key={`${proof.label}-${index}`} className="rounded-xl border border-line bg-panel px-3 py-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge className={sourceBadgeClass(proof.evidence.sourceKind)}>{proof.evidence.sourceKind.replace("_", " ")}</Badge>
                        <Badge className={confidenceBadgeClass(proof.evidence.confidence)}>{proof.evidence.confidence}%</Badge>
                        <span className="text-sm text-text">{proof.label}</span>
                      </div>
                      <div className="mt-1 text-sm text-text">{proof.detail}</div>
                      <div className="mt-1 text-xs text-muted">{proof.evidence.inferenceLabel}</div>
                    </div>
                  ))
                ) : (
                  <div className="text-sm text-muted">No proof points recorded.</div>
                )}
              </div>
            </div>

            <div className="rounded-2xl border border-line bg-panel-2 p-4">
              <div className="text-xs uppercase tracking-[0.18em] text-muted">Missing requirements</div>
              <div className="mt-3 flex flex-wrap gap-2">
                {brief.missingRequirements.length ? (
                  brief.missingRequirements.map((item) => <Badge key={item} className="border-amber-500/40 bg-amber-500/10 text-amber-100">{item}</Badge>)
                ) : (
                  <span className="text-sm text-muted">No blockers recorded on this brief.</span>
                )}
              </div>
            </div>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
