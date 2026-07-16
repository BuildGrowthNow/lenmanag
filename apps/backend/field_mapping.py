#!/usr/bin/env python3
"""
Field mapping guide for SiteBrief → MasterBrief migration
"""

# SiteBrief → MasterBrief field mapping
FIELD_MAPPING = {
    # Tone and voice
    "brief.toneProfile.value": "brief.toneAndVoice",
    "brief.toneProfile": "brief.toneAndVoice",  # For cases where .value is added separately
    # Company and positioning
    "brief.companySummary.value": "brief.valueProposition",
    "brief.companySummary": "brief.valueProposition",
    # Value proposition
    "brief.valuePropositionSummary.value": "brief.valueProposition",
    "brief.valuePropositionSummary": "brief.valueProposition",
    # Audience
    "brief.audienceHypothesis.value": "brief.primaryAudience",
    "brief.audienceHypothesis": "brief.primaryAudience",
    # Conversion/CTA
    "brief.conversionAngle.value": "brief.conversionAction",
    "brief.conversionAngle": "brief.conversionAction",  # Direct access
    "brief.conversionAngle.evidence.confidence": "85",  # Default confidence
    # Hero/headline
    "brief.recommendedHero.value": "brief.headline",
    "brief.recommendedHero": "brief.headline",
    # Sections
    "brief.recommendedSections": "brief.sections",
    # Not available in MasterBrief (return empty/default)
    "brief.sourceCitations": "[]",  # Empty list
    "brief.visualRedesign": "[]",  # Empty list - generated dynamically
    "brief.proofPoints": "[]",  # Empty list - not in MasterBrief
}

# Evidence/confidence patterns
# OLD: brief.conversionAngle.evidence.confidence
# NEW: 85 (default confidence for MasterBrief)

print("Use this mapping when converting SiteBrief accesses to MasterBrief:")
for old, new in FIELD_MAPPING.items():
    print(f"  {old} → {new}")
