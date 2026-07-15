import time
import httpx

BASE_URL = "http://127.0.0.1:52501/api/v1"
EMAIL = "operator@example.com"
NAME = "Operator"
TARGET_URL = "https://taslimifoundation.org"

HEADERS = {
    "X-API-Version": "1",
    "Accept": "application/json",
}


def _print_step(title: str) -> None:
    print("\n===", title, "===", flush=True)


def main() -> None:
    client = httpx.Client(base_url=BASE_URL, headers=HEADERS, timeout=300.0)
    try:
        _print_step("login")
        r = client.post("/auth/login", json={"email": EMAIL, "name": NAME})
        print("status", r.status_code)
        print(r.text)
        r.raise_for_status()
        # Store session cookie
        session_cookie = r.cookies.get("lenquant_session")
        if not session_cookie:
            print("ERROR: No session cookie received")
            return
        client.cookies.set("lenquant_session", session_cookie)

        _print_step("create_lead")
        lead_payload = {
            "companyName": "LenQuant",
            "websiteUrl": TARGET_URL,
            "industry": None,
            "notes": None,
        }
        r = client.post("/leads", json=lead_payload)
        print("status", r.status_code)
        print(r.text)
        r.raise_for_status()
        lead_envelope = r.json()
        lead = lead_envelope.get("data", {}).get("lead") or {}
        lead_id = lead.get("id")
        if not lead_id:
            print("ERROR: lead id missing in response")
            return
        print("lead_id", lead_id)

        _print_step("start_extraction")
        r = client.post(f"/leads/{lead_id}/extraction/start")
        print("status", r.status_code)
        print(r.text)
        r.raise_for_status()
        extraction_envelope = r.json()
        job = extraction_envelope.get("data", {}).get("job") or {}
        job_id = job.get("id")
        if not job_id:
            print("ERROR: extraction job id missing")
            return
        print("extraction_job_id", job_id)

        # Poll extraction job until it finishes or we hit a timeout
        _print_step("wait_for_extraction_job")
        for attempt in range(24):  # up to ~2 minutes
            rj = client.get(f"/jobs/{job_id}")
            rj.raise_for_status()
            payload = rj.json().get("data", {}).get("job") or {}
            status = payload.get("status")
            progress = payload.get("progress")
            step = payload.get("step")
            print(f"attempt {attempt}: status={status} progress={progress} step={step}")
            if status in {"completed", "failed"}:
                break
            time.sleep(5)

        _print_step("extraction_snapshot")
        r = client.get(f"/leads/{lead_id}/extraction")
        print("status", r.status_code)
        print(r.text[:600])
        r.raise_for_status()

        _print_step("create_brief")
        r = client.post(f"/leads/{lead_id}/brief")
        print("status", r.status_code)
        print(r.text[:600])
        r.raise_for_status()

        _print_step("approve_brief")
        r = client.post(f"/leads/{lead_id}/brief/approve")
        print("status", r.status_code)
        print(r.text[:600])
        r.raise_for_status()

        _print_step("generate_site")
        r = client.post(f"/sites/{lead_id}/generate")
        print("status", r.status_code)
        print(r.text[:600])
        r.raise_for_status()
        gen_envelope = r.json()
        gen_job = gen_envelope.get("data", {}).get("job") or {}
        gen_job_id = gen_job.get("id")
        if not gen_job_id:
            print("ERROR: generation job id missing")
            return
        print("generation_job_id", gen_job_id)

        _print_step("wait_for_generation_job")
        for attempt in range(36):  # up to ~3 minutes
            rj = client.get(f"/jobs/{gen_job_id}")
            rj.raise_for_status()
            payload = rj.json().get("data", {}).get("job") or {}
            status = payload.get("status")
            progress = payload.get("progress")
            step = payload.get("step")
            print(f"attempt {attempt}: status={status} progress={progress} step={step}")
            if status in {"completed", "failed"}:
                break
            time.sleep(5)

        _print_step("fetch_generated_site")
        r = client.get(f"/sites/{lead_id}")
        print("status", r.status_code)
        print(r.text[:800])
        r.raise_for_status()
        site = r.json().get("data") or {}
        slug = site.get("previewSlug")
        url = site.get("previewUrl")
        screenshots = site.get("screenshotRefs") or []
        screenshot_url = None
        if isinstance(screenshots, list) and screenshots:
            first = screenshots[0] or {}
            screenshot_url = first.get("url")

        print("\nRESULT preview_slug", slug)
        print("RESULT preview_url", url)
        print("RESULT screenshot_url", screenshot_url)
    finally:
        client.close()


if __name__ == "__main__":
    main()
