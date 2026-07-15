from playwright.sync_api import sync_playwright
import time

url = "http://localhost:3006/sites/6604545f6e6f4887b77d9dd1c7115587"
output_path = "c:/Users/smikl/Desktop/Work/LenManag/taslimifoundation_screenshot.png"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1440, 'height': 900})
    page.goto(url, wait_until="networkidle", timeout=30000)
    time.sleep(2)  # Wait for any animations
    page.screenshot(path=output_path, full_page=True)
    browser.close()

print(f"Screenshot saved to: {output_path}")
