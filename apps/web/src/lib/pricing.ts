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

// Main Pricing Packages
export const MAIN_PACKAGES: PricingOption[] = [
  {
    id: "basic",
    name: "Basic Website",
    price: 1000,
    billingCycle: "one-time",
    description: "Perfect for small businesses and startups",
    category: "main",
    features: [
      { text: "4-5 pages" },
      { text: "Custom design" },
      { text: "Mobile responsive" },
      { text: "Contact form" },
      { text: "Basic SEO" },
    ],
  },
  {
    id: "professional",
    name: "Professional Website",
    price: 2500,
    billingCycle: "one-time",
    description: "Most popular for growing businesses",
    category: "main",
    highlight: true,
    features: [
      { text: "Up to 15 pages" },
      { text: "Advanced custom design" },
      { text: "Mobile responsive" },
      { text: "Contact forms + integrations" },
      { text: "SEO optimization + blog" },
      { text: "Performance optimization" },
    ],
  },
  {
    id: "ecommerce",
    name: "E-Commerce Site",
    price: 3500,
    billingCycle: "one-time",
    description: "Complete online store solution",
    category: "main",
    features: [
      { text: "Full e-commerce functionality" },
      { text: "Product management" },
      { text: "Payment processing" },
      { text: "Inventory system" },
      { text: "Customer dashboard" },
      { text: "Order management" },
    ],
  },
];

// Add-on Services
export const ADD_ON_SERVICES: PricingOption[] = [
  {
    id: "extra_pages",
    name: "Additional Pages",
    price: 150,
    billingCycle: "one-time",
    description: "Per page",
    category: "addon",
    features: [
      { text: "Up to 50 pages total" },
      { text: "Same design quality" },
      { text: "Full performance" },
    ],
  },
  {
    id: "advanced_features",
    name: "Advanced Features",
    price: 300,
    billingCycle: "one-time",
    description: "Custom functionality",
    category: "addon",
    features: [
      { text: "Custom integrations" },
      { text: "API connections" },
      { text: "Special functionality" },
    ],
  },
];

// Recurring Services
export const RECURRING_SERVICES: PricingOption[] = [
  {
    id: "maintenance",
    name: "Maintenance Service",
    price: 500,
    billingCycle: "monthly",
    description: "Ongoing support and updates",
    category: "service",
    features: [
      { text: "1-hour strategy meeting/month" },
      { text: "3 requested changes/month" },
      { text: "Performance monitoring" },
      { text: "Security updates" },
    ],
  },
  {
    id: "hosting",
    name: "Hosting Service",
    price: 200,
    billingCycle: "monthly",
    description: "Hosting only",
    category: "service",
    features: [
      { text: "Fast, reliable infrastructure" },
      { text: "Auto-scaling" },
      { text: "SSL certificate" },
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
