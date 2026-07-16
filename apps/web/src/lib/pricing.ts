export interface Feature {
  text: string;
  limit?: number | "unlimited";
  description?: string;
}

export interface PricingOption {
  id: string;
  name: string;
  price: number;
  billingCycle: "one-time" | "monthly";
  description: string;
  features: Feature[];
  highlight?: boolean;
  category: "main" | "addon" | "service";
}

export interface AddOn {
  id: string;
  name: string;
  description: string;
  price: number;
  type: "toggle" | "quantity";
  maxQuantity?: number;
  popular?: boolean;
}

export const BASE_PRICE = 1000;
export const BASE_PAGES = 1;
export const CURRENCY = "usd";

// Main Package (Only One)
export const MAIN_PACKAGE: PricingOption = {
  id: "professional",
  name: "Professional Website",
  price: 1000,
  billingCycle: "one-time",
  description: "Everything you need to get online",
  category: "main",
  highlight: true,
  features: [
    { text: "Landing page" },
    { text: "Beautiful design that matches your brand" },
    { text: "Works perfectly on phones and tablets" },
    { text: "Easy way for customers to contact you" },
  ],
};

// Extra Services (Collapsible Dropdown Section)
export const EXTRA_SERVICES: PricingOption[] = [
  {
    id: "extra_pages",
    name: "Additional Pages",
    price: 150,
    billingCycle: "one-time",
    description: "Per page (up to 50 pages)",
    category: "addon",
    features: [
      { text: "Add more pages to your site" },
      { text: "Same beautiful design quality" },
    ],
  },
  {
    id: "advanced_features",
    name: "Advanced Features",
    price: 300,
    billingCycle: "one-time",
    description: "Starting at $300",
    category: "addon",
    features: [
      { text: "Connect to special tools" },
      { text: "Custom functionality for your business" },
      { text: "API integrations" },
    ],
  },
  {
    id: "maintenance",
    name: "Maintenance Service",
    price: 500,
    billingCycle: "monthly",
    description: "Ongoing support and updates",
    category: "service",
    features: [
      { text: "1-hour strategy meeting every month" },
      { text: "3 updates or changes per month" },
      { text: "We watch your site's performance" },
      { text: "Keep everything secure" },
    ],
  },
  {
    id: "hosting",
    name: "Hosting Service",
    price: 200,
    billingCycle: "monthly",
    description: "Fast and reliable hosting",
    category: "service",
    features: [
      { text: "Fast, reliable website hosting" },
      { text: "Automatic scaling" },
      { text: "Secure SSL certificate" },
      { text: "Automatic backups" },
    ],
  },
];

export const ADD_ONS: AddOn[] = [
  {
    id: "extra_pages",
    name: "Extra Pages",
    description: "Additional pages beyond the included landing page (up to 4 more)",
    price: 200,
    type: "quantity",
    maxQuantity: 4,
  },
  {
    id: "custom_domain",
    name: "Custom Domain",
    description: "Domain registration, DNS setup & SSL certificate",
    price: 150,
    type: "toggle",
  },
  {
    id: "advanced_seo",
    name: "Advanced SEO",
    description: "Keyword research, schema markup, sitemap & Search Console setup",
    price: 300,
    type: "toggle",
    popular: true,
  },
  {
    id: "blog_cms",
    name: "Blog / CMS",
    description: "Content management system with blog functionality",
    price: 250,
    type: "toggle",
  },
  {
    id: "analytics_tracking",
    name: "Analytics & Tracking",
    description: "GA4, heatmaps & conversion tracking setup",
    price: 100,
    type: "toggle",
  },
  {
    id: "priority_delivery",
    name: "Priority Delivery (1 day)",
    description: "Get your website delivered in 24 hours instead of 3 days",
    price: 500,
    type: "toggle",
  },
];

export interface SelectedAddOns {
  [addonId: string]: number; // quantity (0 = not selected, 1+ = selected/qty)
}

export function calculateTotal(selectedAddOns: SelectedAddOns): number {
  let total = BASE_PRICE;
  for (const addon of ADD_ONS) {
    const qty = selectedAddOns[addon.id] || 0;
    total += addon.price * qty;
  }
  return total;
}

export function getSelectedItems(selectedAddOns: SelectedAddOns) {
  const items: { name: string; price: number; quantity: number }[] = [
    { name: "Professional Website (Landing Page)", price: BASE_PRICE, quantity: 1 },
  ];
  for (const addon of ADD_ONS) {
    const qty = selectedAddOns[addon.id] || 0;
    if (qty > 0) {
      items.push({ name: addon.name, price: addon.price, quantity: qty });
    }
  }
  return items;
}
