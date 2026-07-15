import httpx
import time

BASE_URL = "http://127.0.0.1:8003/api/v1"
EMAIL = "operator@example.com"
NAME = "Operator"

client = httpx.Client(base_url=BASE_URL, timeout=300.0)

# Login
r = client.post("/auth/login", json={"email": EMAIL, "name": NAME})
session_cookie = r.cookies.get("lenquant_session")
client.cookies.set("lenquant_session", session_cookie)
print("Logged in")

# Use the existing lead ID
lead_id = "b7d2d2d3f4ad4cb7900c7be1c2e86c12"

# Generate site
r = client.post(f"/sites/{lead_id}/generate")
print(f"Generate status: {r.status_code}")
job_data = r.json()
job_id = job_data["data"]["job"]["id"]
print(f"Job ID: {job_id}")

# Wait for job to complete
for i in range(30):
    r = client.get(f"/jobs/{job_id}")
    job = r.json()["data"]["job"]
    print(f"Attempt {i}: status={job['status']} progress={job['progress']} step={job['step']}")
    if job["status"] == "completed":
        break
    time.sleep(2)

# Fetch the site
r = client.get(f"/sites/{lead_id}")
site = r.json()["data"]
print(f"\nSite ID: {site['id']}")
print(f"Preview slug: {site.get('previewSlug')}")
print(f"Hero headline: {site.get('heroVariant', {}).get('headline')}")
print(f"Section stack length: {len(site.get('sectionStack', []))}")
