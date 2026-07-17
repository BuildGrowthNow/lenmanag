'use client';

/**
 * Client component for master brief review and approval
 */

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  type MasterBrief,
  approveMasterBrief,
  refineMasterBrief,
} from '@/lib/api/master-brief';

interface BriefReviewClientProps {
  leadId: string;
  initialBrief: MasterBrief;
}

export function BriefReviewClient({ leadId, initialBrief }: BriefReviewClientProps) {
  const router = useRouter();
  const [brief, setBrief] = useState(initialBrief);
  const [feedback, setFeedback] = useState('');
  const [isRefining, setIsRefining] = useState(false);
  const [isApproving, setIsApproving] = useState(false);
  const [showFeedback, setShowFeedback] = useState(false);

  const handleRefine = async () => {
    if (!feedback.trim()) return;

    setIsRefining(true);
    try {
      const updated = await refineMasterBrief(leadId, feedback);
      setBrief(updated);
      setFeedback('');
      setShowFeedback(false);
    } catch (error) {
      console.error('Failed to refine brief:', error);
      alert(error instanceof Error ? error.message : 'Failed to refine brief');
    } finally {
      setIsRefining(false);
    }
  };

  const handleApprove = async () => {
    if (!confirm('Approve this brief and start site generation?')) return;

    setIsApproving(true);
    try {
      await approveMasterBrief(leadId);
      router.push(`/app/leads/${leadId}`);
      router.refresh();
    } catch (error) {
      console.error('Failed to approve brief:', error);
      alert(error instanceof Error ? error.message : 'Failed to approve brief');
    } finally {
      setIsApproving(false);
    }
  };

  const motionLabel = {
    none: 'None',
    subtle: 'Subtle',
    moderate: 'Moderate',
    dramatic: 'Dramatic',
  }[brief.motionLevel];

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-50 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold">Master Brief Review</h1>
            <p className="text-sm text-zinc-400 mt-1">
              Version {brief.version} • Confidence: {brief.confidenceScore}%
            </p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => setShowFeedback(!showFeedback)}
              className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 rounded-lg transition-colors"
            >
              Request Changes
            </button>
            <button
              onClick={handleApprove}
              disabled={isApproving || brief.approvalState === 'approved'}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-zinc-700 disabled:text-zinc-500 rounded-lg transition-colors"
            >
              {isApproving ? 'Approving...' : 'Approve & Generate'}
            </button>
          </div>
        </div>

        {/* Feedback Input */}
        {showFeedback && (
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 space-y-3">
            <textarea
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              placeholder="Describe what changes you'd like (e.g., 'make it bolder', 'add a pricing section', 'less corporate tone')"
              className="w-full h-24 px-3 py-2 bg-zinc-800 border border-zinc-700 rounded text-sm focus:outline-none focus:border-blue-500 resize-none"
            />
            <div className="flex gap-2">
              <button
                onClick={handleRefine}
                disabled={isRefining || !feedback.trim()}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-zinc-700 disabled:text-zinc-500 rounded text-sm transition-colors"
              >
                {isRefining ? 'Refining...' : 'Regenerate Brief'}
              </button>
              <button
                onClick={() => {
                  setShowFeedback(false);
                  setFeedback('');
                }}
                className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 rounded text-sm transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Two Column Layout */}
        <div className="grid grid-cols-3 gap-6">
          {/* Left Panel - Brief Content */}
          <div className="col-span-2 space-y-6">
            {/* Hero Preview */}
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-6 space-y-4">
              <h2 className="text-lg font-semibold text-zinc-300">Hero</h2>
              <div className="space-y-3">
                <div>
                  <p className="text-3xl font-bold">{brief.headline}</p>
                  {brief.subheadline && (
                    <p className="text-lg text-zinc-400 mt-2">{brief.subheadline}</p>
                  )}
                </div>
                <div className="flex gap-2 text-sm">
                  <span className="px-2 py-1 bg-zinc-800 rounded">
                    {brief.visualStyle}
                  </span>
                  <span className="px-2 py-1 bg-zinc-800 rounded">
                    Motion: {motionLabel}
                  </span>
                </div>
              </div>
            </div>

            {/* Strategic Foundation */}
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-6 space-y-4">
              <h2 className="text-lg font-semibold text-zinc-300">Strategic Foundation</h2>
              <div className="space-y-3">
                <div>
                  <h3 className="text-sm text-zinc-500 mb-1">Business Goal</h3>
                  <p className="text-sm">{brief.businessGoal}</p>
                </div>
                <div>
                  <h3 className="text-sm text-zinc-500 mb-1">Primary Audience</h3>
                  <p className="text-sm">{brief.primaryAudience}</p>
                </div>
                <div>
                  <h3 className="text-sm text-zinc-500 mb-1">Value Proposition</h3>
                  <p className="text-sm">{brief.valueProposition}</p>
                </div>
                <div>
                  <h3 className="text-sm text-zinc-500 mb-1">Tone & Voice</h3>
                  <p className="text-sm">{brief.toneAndVoice}</p>
                </div>
              </div>
            </div>

            {/* Sections */}
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-6 space-y-4">
              <h2 className="text-lg font-semibold text-zinc-300">
                Page Sections ({brief.sections.length})
              </h2>
              <div className="space-y-4">
                {brief.sections.map((section, index) => (
                  <div
                    key={index}
                    className="p-4 bg-zinc-800 border border-zinc-700 rounded space-y-2"
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <h3 className="font-medium">{section.headline}</h3>
                        <p className="text-xs text-zinc-500 mt-0.5">{section.purpose}</p>
                      </div>
                      <span className="text-xs px-2 py-1 bg-zinc-700 rounded">
                        {section.suggestedApproach}
                      </span>
                    </div>
                    <p className="text-sm text-zinc-400">{section.contentSummary}</p>
                    {section.contentPoints.length > 0 && (
                      <ul className="text-xs text-zinc-500 space-y-1 mt-2">
                        {section.contentPoints.slice(0, 3).map((point, i) => (
                          <li key={i}>• {point}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Creative Direction */}
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-6 space-y-4">
              <h2 className="text-lg font-semibold text-zinc-300">Creative Direction</h2>

              {brief.creativeDirection && (
                <div className="space-y-4">
                  <div className="p-4 bg-gradient-to-r from-blue-950/30 to-purple-950/30 border border-blue-900/30 rounded-lg">
                    <h3 className="text-sm text-blue-400 mb-1">Design Concept</h3>
                    <p className="text-sm font-medium">{brief.creativeDirection.designConcept}</p>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <h3 className="text-sm text-zinc-500 mb-1">Hero Treatment</h3>
                      <p className="text-sm">{brief.creativeDirection.heroTreatment}</p>
                    </div>
                    <div>
                      <h3 className="text-sm text-zinc-500 mb-1">Signature Technique</h3>
                      <p className="text-sm text-blue-400">{brief.creativeDirection.signatureTechnique}</p>
                    </div>
                    <div>
                      <h3 className="text-sm text-zinc-500 mb-1">Layout Strategy</h3>
                      <p className="text-sm">{brief.creativeDirection.layoutStrategy}</p>
                    </div>
                    <div>
                      <h3 className="text-sm text-zinc-500 mb-1">Scroll Behavior</h3>
                      <p className="text-sm">{brief.creativeDirection.scrollBehavior}</p>
                    </div>
                    <div>
                      <h3 className="text-sm text-zinc-500 mb-1">Color Mood</h3>
                      <p className="text-sm">{brief.creativeDirection.colorMood}</p>
                    </div>
                    <div>
                      <h3 className="text-sm text-zinc-500 mb-1">Typography</h3>
                      <p className="text-sm">{brief.creativeDirection.typographyPersonality}</p>
                    </div>
                  </div>

                  {brief.creativeDirection.microInteractions.length > 0 && (
                    <div>
                      <h3 className="text-sm text-zinc-500 mb-2">Micro-interactions</h3>
                      <div className="flex flex-wrap gap-2">
                        {brief.creativeDirection.microInteractions.map((item) => (
                          <span key={item} className="text-xs px-2 py-1 bg-green-900/30 text-green-400 rounded">
                            {item}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {brief.creativeDirection.inspirationKeywords.length > 0 && (
                    <div>
                      <h3 className="text-sm text-zinc-500 mb-2">Inspiration Keywords</h3>
                      <div className="flex flex-wrap gap-2">
                        {brief.creativeDirection.inspirationKeywords.map((keyword) => (
                          <span key={keyword} className="text-xs px-2 py-1 bg-purple-900/30 text-purple-400 rounded">
                            {keyword}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {brief.creativeDirection.avoidPatterns.length > 0 && (
                    <div>
                      <h3 className="text-sm text-zinc-500 mb-2">Avoid These Patterns</h3>
                      <div className="flex flex-wrap gap-2">
                        {brief.creativeDirection.avoidPatterns.map((pattern) => (
                          <span key={pattern} className="text-xs px-2 py-1 bg-red-900/30 text-red-400 rounded line-through">
                            {pattern}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              <div className="grid grid-cols-2 gap-4 pt-4 border-t border-zinc-800">
                <div>
                  <h3 className="text-sm text-zinc-500 mb-1">Visual Style</h3>
                  <p className="text-sm">{brief.visualStyle}</p>
                </div>
                <div>
                  <h3 className="text-sm text-zinc-500 mb-1">Color Strategy</h3>
                  <p className="text-sm">{brief.colorStrategy}</p>
                </div>
                <div>
                  <h3 className="text-sm text-zinc-500 mb-1">Motion Level</h3>
                  <p className="text-sm">{motionLabel}</p>
                </div>
                <div>
                  <h3 className="text-sm text-zinc-500 mb-1">CTA Strategy</h3>
                  <p className="text-sm">{brief.ctaStrategy}</p>
                </div>
              </div>

              {brief.specialEffects.length > 0 && (
                <div>
                  <h3 className="text-sm text-zinc-500 mb-2">Special Effects</h3>
                  <div className="flex flex-wrap gap-2">
                    {brief.specialEffects.map((effect) => (
                      <span
                        key={effect}
                        className="text-xs px-2 py-1 bg-zinc-800 rounded"
                      >
                        {effect}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Right Panel - AI Reasoning & Metadata */}
          <div className="space-y-6">
            {/* Confidence & Status */}
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 space-y-3">
              <div>
                <h3 className="text-sm text-zinc-500 mb-1">Confidence Score</h3>
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-2 bg-zinc-800 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-blue-600 rounded-full"
                      style={{ width: `${brief.confidenceScore}%` }}
                    />
                  </div>
                  <span className="text-sm font-medium">{brief.confidenceScore}%</span>
                </div>
              </div>
              <div>
                <h3 className="text-sm text-zinc-500 mb-1">Status</h3>
                <p className="text-sm capitalize">{brief.approvalState.replace('_', ' ')}</p>
              </div>
            </div>

            {/* AI Reasoning */}
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 space-y-2">
              <h3 className="text-sm font-medium text-zinc-300">AI Reasoning</h3>
              <p className="text-xs text-zinc-400 leading-relaxed">{brief.aiReasoning}</p>
            </div>

            {/* Brand Assets */}
            {(brief.brandAssets.logoUrl ||
              brief.brandAssets.primaryColor ||
              brief.brandAssets.fontFamily) && (
              <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 space-y-3">
                <h3 className="text-sm font-medium text-zinc-300">Brand Assets</h3>
                {brief.brandAssets.primaryColor && (
                  <div className="flex items-center gap-2">
                    <div
                      className="w-6 h-6 rounded border border-zinc-700"
                      style={{ backgroundColor: brief.brandAssets.primaryColor }}
                    />
                    <span className="text-xs text-zinc-400">
                      {brief.brandAssets.primaryColor}
                    </span>
                  </div>
                )}
                {brief.brandAssets.fontFamily && (
                  <div className="text-xs text-zinc-400">
                    Font: {brief.brandAssets.fontFamily}
                  </div>
                )}
                {brief.brandAssets.logoUrl && (
                  <div className="text-xs text-zinc-500">Logo: Captured</div>
                )}
              </div>
            )}

            {/* Feedback History */}
            {brief.feedbackHistory.length > 0 && (
              <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 space-y-2">
                <h3 className="text-sm font-medium text-zinc-300">Feedback History</h3>
                <div className="space-y-2">
                  {brief.feedbackHistory.map((item, index) => (
                    <div key={index} className="text-xs text-zinc-400 p-2 bg-zinc-800 rounded">
                      {item}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Missing Requirements */}
            {brief.missingRequirements.length > 0 && (
              <div className="bg-amber-950/20 border border-amber-900/30 rounded-lg p-4 space-y-2">
                <h3 className="text-sm font-medium text-amber-400">Missing Requirements</h3>
                <ul className="text-xs text-amber-300 space-y-1">
                  {brief.missingRequirements.map((req, index) => (
                    <li key={index}>• {req}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
