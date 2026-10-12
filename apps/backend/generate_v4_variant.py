"""
One-shot script: generate html_v4 variant for Stephen's Landscaping (lead c72f68b9fe304793b0a75f2b1ab8c6b3).
Run inside the backend container: python generate_v4_variant.py
"""

import asyncio
import os
import sys

LEAD_ID = "c72f68b9fe304793b0a75f2b1ab8c6b3"
USER_ID = "6a58dca0e7b391f8bf5a3177"
VARIANT_TYPE = "html_v4"


async def main() -> None:
    # Bootstrap the app context
    from app.core.database import init_db
    from app.core.sites import site_repository
    from app.core.leads import lead_repository
    from app.core.variant_strategy import get_variant_strategies

    await init_db()

    lead = await lead_repository.get_lead(LEAD_ID, user_id=USER_ID)
    if lead is None:
        print(f"ERROR: Lead {LEAD_ID} not found")
        sys.exit(1)
    print(f"Lead: {lead.companyName}")

    # Load extraction
    extraction = await lead_repository.get_extraction_snapshot(LEAD_ID)
    if extraction is None:
        print("ERROR: No extraction found for lead")
        sys.exit(1)
    print("Extraction loaded")

    # Load analysis
    analysis = await lead_repository.get_analysis(LEAD_ID)
    print(f"Analysis loaded: {analysis is not None}")

    # Check if v4 already exists
    existing = await site_repository.list_sites_by_lead(LEAD_ID, user_id=USER_ID)
    for site in existing:
        if site.variantType == VARIANT_TYPE:
            print(f"html_v4 already exists: {site.id} slug={site.previewSlug}")
            return

    strategies = get_variant_strategies(lead.industry)
    strategy = strategies[VARIANT_TYPE]
    print(f"Strategy: {strategy['variantLabel']}")

    # Generate the variant
    print("Generating html_v4 variant (this may take 2-3 minutes)...")
    site = await site_repository.generate_site_variant(
        lead_id=LEAD_ID,
        variant_type=VARIANT_TYPE,
        variant_strategy=dict(strategy),
        extraction=extraction,
        analysis=analysis,
        user_id=USER_ID,
    )

    print(f"Generated site: {site.id}")
    print(f"Preview slug: {site.previewSlug}")
    print(f"Variant label: {site.variantLabel}")
    print(f"Quality score: {site.qualityScore}")
    print(f"Preview URL: https://sites.lenquant.com/st/{site.previewSlug}")


if __name__ == "__main__":
    asyncio.run(main())
