import asyncio
from app.core.sites import site_repository

async def test():
    print('Checking in-memory storage...')
    async with site_repository._memory_lock:
        print(f'Number of sites in memory: {len(site_repository._sites)}')
        for site_id, doc in site_repository._sites.items():
            print(f'  Site ID: {site_id}')
            print(f'  Preview Slug: {doc.get("previewSlug")}')
            print(f'  Lead ID: {doc.get("leadId")}')
            print()

asyncio.run(test())
