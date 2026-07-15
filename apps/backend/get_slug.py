import sys
sys.path.append('c:/Users/smikl/Desktop/Work/LenManag/apps/backend')
import asyncio
from app.core.mongo import get_database

async def main():
    db = await get_database()
    doc = await db.sites.find_one()
    if doc:
        print(f"Slug: {doc.get('previewSlug')}, ID: {doc.get('_id') or doc.get('id')}")
    else:
        print("No sites found")

asyncio.run(main())
