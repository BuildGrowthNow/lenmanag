from playwright.sync_api import sync_playwright
import time

url = "http://localhost:3002/sites/a8dd9f7c1e1344c5b03b9e5bf82747aa"


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Run with visible browser to debug
        page = browser.new_page(viewport={"width": 1440, "height": 900})

        # Enable console logging
        page.on("console", lambda msg: print(f"Console: {msg.text}"))

        # Enable network logging
        def log_request(request):
            print(f"Request: {request.method} {request.url}")

        page.on("request", log_request)

        def log_response(response):
            print(f"Response: {response.status} {response.url}")

        page.on("response", log_response)

        page.goto(url, wait_until="networkidle", timeout=30000)
        time.sleep(5)  # Wait longer to see what happens
        browser.close()


if __name__ == "__main__":
    main()
