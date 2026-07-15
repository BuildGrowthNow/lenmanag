from playwright.sync_api import sync_playwright
import time
import json

url = "http://localhost:3002/sites/b7d2d2d3f4ad4cb7900c7be1c2e86c12"


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=500)
        page = browser.new_page(viewport={"width": 1440, "height": 900})

        # Enable console logging
        page.on("console", lambda msg: print(f"Console [{msg.type}]: {msg.text}"))

        # Enable network logging
        def log_request(request):
            print(f"Request: {request.method} {request.url}")

        page.on("request", log_request)

        def log_response(response):
            print(f"Response: {response.status} {response.url}")
            if "/api/v1/public/sites/" in response.url:
                try:
                    body = response.json()
                    print(f"API Response keys: {list(body.keys())}")
                    if "data" in body:
                        print(f"Site data keys: {list(body['data'].keys())}")
                        print(
                            f"Hero headline: {body['data'].get('heroVariant', {}).get('headline')}"
                        )
                except Exception:
                    print("Could not parse JSON response")

        page.on("response", log_response)

        page.goto(url, wait_until="networkidle", timeout=30000)

        # Wait for React to render
        time.sleep(5)

        # Check page content
        body_text = page.evaluate("() => document.body.innerText")
        print(f"\nPage body text (first 500 chars):\n{body_text[:500]}")

        # Check if "Preview not available" is on the page
        has_error = page.evaluate(
            "() => document.body.innerText.includes('Preview not available')"
        )
        print(f"\nContains 'Preview not available': {has_error}")

        # Check for hero headline
        has_hero = page.evaluate(
            "() => document.body.innerText.includes('Champion Well Drilling')"
        )
        print(f"Contains 'Champion Well Drilling': {has_hero}")

        time.sleep(5)
        browser.close()


if __name__ == "__main__":
    main()
