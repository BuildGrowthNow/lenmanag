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
