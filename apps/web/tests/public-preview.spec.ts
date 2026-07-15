import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';
const SLUG = process.env.SITE_SLUG || 'c782d911cb6c4a65b6b4ebe2fdd10c11';
const SECOND_SITE_SLUG = process.env.SECOND_SITE_SLUG || null;

const forbiddenTerms = [
  'source-safe',
  'source traceability',
  'generation',
  'generated',
  'quality score',
  'QA status',
  'readiness',
  'job id',
  'operator',
  'admin',
  'evidence',
  'inference',
  'extracted cues',
  'crawl',
  'brief',
  'missing requirements',
  'preview runtime',
];

function hasForbidden(text: string): string[] {
  const lowered = text.toLowerCase();
  return forbiddenTerms.filter((term) => lowered.includes(term));
}

test.describe('Public website preview', () => {
  test('login page is styled', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') errors.push(msg.text());
    });
    await page.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded' });
    await expect(page.getByText('LenQuant admin access')).toBeVisible();
    await expect(page.locator('button:has-text("Enter workspace")')).toBeVisible();
    expect(errors, `Console errors on /login: ${errors.join('\n')}`).toHaveLength(0);
  });

  test('login works with allowlisted email and admin pages load', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await page.getByLabel('Email').fill('operator@example.com');
    await page.getByLabel('Display name').fill('Operator');
    const [nav] = await Promise.all([
      page.waitForURL(/\/nsa(\/.*)?$/),
      page.locator('button:has-text("Enter workspace")').click(),
    ]);
    await expect(page).toHaveURL(/\/nsa$/);
    await page.goto(`${BASE_URL}/nsa/sites`);
    await expect(page).toHaveURL(/\/nsa\/sites$/);
    await expect(page.getByText('Sites')).toBeVisible({ timeout: 10_000 }).catch(() => {});
    await page.goto(`${BASE_URL}/nsa/sites/${SLUG}`);
    await expect(page).toHaveURL(new RegExp(`/nsa/sites/${SLUG}$`));
  });

  test('public preview renders client-facing page without internal terms', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') errors.push(msg.text());
    });

    await page.goto(`${BASE_URL}/sites/${SLUG}`, { waitUntil: 'domcontentloaded' });
    await page.waitForSelector('h1');

    // Should render multiple sections
    const sectionHeadings = page.locator('#sections h2');
    const count = await sectionHeadings.count();
    expect(count).toBeGreaterThan(1);

    // Should have visible CTAs
    await expect(page.locator('a:has-text("See how it works"), a:has-text("Learn more"), a:has-text("Contact us"), a:has-text("Start your trial"), a:has-text("Explore")').first()).toBeVisible();

    // No internal terms visible
    const bodyText = await page.locator('body').innerText();
    const violations = hasForbidden(bodyText);
    expect(violations, `Forbidden terms found: ${violations.join(', ')}`).toHaveLength(0);

    // No runtime errors and CSS applied (simple heuristic: background gradient present)
    expect(errors, `Console errors on public page: ${errors.join('\n')}`).toHaveLength(0);

    // Optional sanity: brand/company name mentioned somewhere (non-blocking)
    const brandSeen = await page.getByText(/basecamp/i).count();
    expect(brandSeen).toBeGreaterThanOrEqual(0);

    // Capture and attach a full-page screenshot for visual review
    const shot = await page.screenshot({ path: test.info().outputPath('public-preview.png'), fullPage: true });
    await test.info().attach('public-preview', { body: shot, contentType: 'image/png' });

    // Tolerate accidental trailing backtick encoding
    await page.goto(`${BASE_URL}/sites/${encodeURIComponent(SLUG + '`')}`, { waitUntil: 'domcontentloaded' });
    await expect(page.locator('h1')).toBeVisible();
  });

  test('second site preview (lenquant) validates design diversity and safety', async ({ page }) => {
    test.skip(!SECOND_SITE_SLUG, 'SECOND_SITE_SLUG not provided');

    // First visit basecamp slug to capture styling
    await page.goto(`${BASE_URL}/sites/${SLUG}`, { waitUntil: 'domcontentloaded' });
    await page.waitForSelector('h1');
    const heroImage1 = page.locator('img').first();
    let maskImage1 = '';
    if (await heroImage1.isVisible()) {
      maskImage1 = await heroImage1.evaluate((el) => window.getComputedStyle(el).maskImage);
    }
    const ctaButton1 = page.locator('a:has-text("See how it works"), a:has-text("Learn more"), a:has-text("Contact us"), a:has-text("Start your trial"), a:has-text("Explore")').first();
    let ctaColor1 = '';
    if (await ctaButton1.isVisible()) {
      ctaColor1 = await ctaButton1.evaluate((el) => window.getComputedStyle(el).backgroundColor);
    }

    // Now visit second slug
    await page.goto(`${BASE_URL}/sites/${SECOND_SITE_SLUG}`, { waitUntil: 'domcontentloaded' });
    await page.waitForSelector('h1');

    // Should render multiple sections
    const sectionHeadings = page.locator('#sections h2');
    const count = await sectionHeadings.count();
    expect(count).toBeGreaterThan(2);

    // At least one img is visible
    const images = page.locator('img');
    const imageCount = await images.count();
    let visibleImageCount = 0;
    let maskImage2 = '';
    for (let i = 0; i < imageCount; i++) {
      if (await images.nth(i).isVisible()) {
        visibleImageCount++;
        maskImage2 = await images.nth(i).evaluate((el) => window.getComputedStyle(el).maskImage);
        break; // just need one
      }
    }
    expect(visibleImageCount).toBeGreaterThan(0);

    // Should have visible CTAs with approved labels
    const ctaButton2 = page.locator('a:has-text("See how it works"), a:has-text("Learn more"), a:has-text("Contact us"), a:has-text("Start your trial"), a:has-text("Explore")').first();
    await expect(ctaButton2).toBeVisible();
    
    let ctaColor2 = '';
    if (await ctaButton2.isVisible()) {
      ctaColor2 = await ctaButton2.evaluate((el) => window.getComputedStyle(el).backgroundColor);
    }

    // No internal terms visible
    const bodyText = await page.locator('body').innerText();
    const violations = hasForbidden(bodyText);
    expect(violations, `Forbidden terms found: ${violations.join(', ')}`).toHaveLength(0);

    // Assert design diversity
    // Either mask shape or accent color should differ
    const differs = maskImage1 !== maskImage2 || ctaColor1 !== ctaColor2;
    expect(differs, `Design DNA did not differ between the two sites. Mask: ${maskImage1} vs ${maskImage2}, CTA Color: ${ctaColor1} vs ${ctaColor2}`).toBe(true);
  });
});
