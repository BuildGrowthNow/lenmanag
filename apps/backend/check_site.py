import asyncio
from app.core.sites import site_repository

async def test():
    slug = 'a8dd9f7c1e1344c5b03b9e5bf82747aa'
    site = await site_repository.get_site_by_slug(slug)
    if site:
        print('Site found:')
        print('ID:', site.id)
        print('Lead ID:', site.leadId)
        print('Theme:', site.themeId)
        print('Section stack length:', len(site.sectionStack) if site.sectionStack else 0)
        print('Hero headline:', site.heroVariant.headline if site.heroVariant else None)
    else:
        print('Site not found with slug:', slug)
    
    # Also try getting by ID
    site_by_id = await site_repository.get_site(slug)
    if site_by_id:
        print('\nSite found by ID:')
        print('ID:', site_by_id.id)
        print('Lead ID:', site_by_id.leadId)
    else:
        print('\nSite not found by ID either')

asyncio.run(test())
