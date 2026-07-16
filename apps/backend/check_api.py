import httpx

slug = "b7d2d2d3f4ad4cb7900c7be1c2e86c12"
url = f"http://127.0.0.1:8003/api/v1/public/sites/{slug}"

r = httpx.get(url)
print(f"Status: {r.status_code}")
print(f"Response: {r.text[:500]}")
