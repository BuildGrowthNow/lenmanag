import httpx
import json

slug = "a8dd9f7c1e1344c5b03b9e5bf82747aa"
url = f"http://127.0.0.1:8003/api/v1/public/sites/{slug}"

r = httpx.get(url)
print(f"Status: {r.status_code}")
if r.status_code == 200:
    data = r.json()
    site = data["data"]
    print(f"Site ID: {site.get('id')}")
    print(f"Lead ID: {site.get('leadId')}")
    print(f"Theme: {site.get('themeId')}")
    print(f"Palette Mode: {site.get('paletteMode')}")
    print(f"Hero headline: {site.get('heroVariant', {}).get('headline')}")
    print(f"Section stack length: {len(site.get('sectionStack', []))}")
    print(
        f"First section: {site.get('sectionStack', [{}])[0].get('headline') if site.get('sectionStack') else 'None'}"
    )
    print("\nFull response saved to site_data.json")
    with open("site_data.json", "w") as f:
        json.dump(data, f, indent=2)
else:
    print(f"Error: {r.text}")
