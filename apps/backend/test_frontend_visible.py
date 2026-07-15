from playwright.sync_api import sync_playwright
import time

url = "http://localhost:3002/sites/b7d2d2d3f4ad4cb7900c7be1c2e86c12"


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=1000)  # Slow motion to see what happens
        page = browser.new_page(viewport={"width": 1440, "height": 900})

        # Enable console logging
        page.on("console", lambda msg: print(f"Console [{msg.type}]: {msg.text}"))

        # Enable network logging
        def log_request(request):
            print(f"Request: {request.method} {request.url}")

        page.on("request", log_request)

        def log_response(response):
            print(f"Response: {response.status} {response.url}")
            if response.status >= 400:
                print(f"Error body: {response.text}")

        page.on("response", log_response)

        page.goto(url, wait_until="networkidle", timeout=30000)
        time.sleep(10)  # Wait longer to see the page
        browser.close()


if __name__ == "__main__":
    main()
