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

export interface ExtraService extends PricingOption {
  type: "toggle" | "quantity";
  maxQuantity?: number;
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
export const EXTRA_SERVICES: ExtraService[] = [
  {
    id: "extra_pages",
    name: "Additional Pages",
    price: 50,
    billingCycle: "one-time",
    description: "Per page (up to 50 pages)",
    category: "addon",
    type: "quantity",
    maxQuantity: 50,
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
    type: "toggle",
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
    type: "toggle",
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
    type: "toggle",
    features: [
      { text: "Fast, reliable website hosting" },
      { text: "Automatic scaling" },
      { text: "Secure SSL certificate" },
      { text: "Automatic backups" },
    ],
  },
];

export interface SelectedAddOns {
  [serviceId: string]: number; // 0 = not selected, 1 = toggle selected, 2+ = quantity
}

export function calculateTotal(selectedServices: SelectedAddOns): number {
  let total = BASE_PRICE;
  for (const service of EXTRA_SERVICES) {
    const qty = selectedServices[service.id] || 0;
    total += service.price * qty;
  }
  return total;
}

export function getSelectedItems(selectedServices: SelectedAddOns) {
  const items: { id: string; name: string; price: number; quantity: number; billingCycle: "one-time" | "monthly" }[] = [
    { id: "professional", name: "Professional Website", price: BASE_PRICE, quantity: 1, billingCycle: "one-time" },
  ];
  for (const service of EXTRA_SERVICES) {
    const qty = selectedServices[service.id] || 0;
    if (qty > 0) {
      items.push({
        id: service.id,
        name: service.name,
        price: service.price,
        quantity: qty,
        billingCycle: service.billingCycle,
      });
    }
  }
  return items;
}
