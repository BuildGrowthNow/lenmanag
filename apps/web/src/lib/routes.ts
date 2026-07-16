export const pipelineRoutes = [
  { href: "/app", label: "Dashboard", hint: "Overview" },
  { href: "/app/leads", label: "Leads", hint: "Import and track" },
  { href: "/app/sites", label: "Websites", hint: "Generated previews" },
  { href: "/app/review", label: "Review", hint: "QA queue" },
  { href: "/app/messages", label: "Messages", hint: "Drafts and ready states" },
];

export const outreachRoutes = [
  { href: "/app/analytics", label: "Analytics", hint: "Visits and clicks" },
];

export const opsRoutes = [
  { href: "/app/scale", label: "Scale", hint: "Queues & retries" },
  { href: "/app/orders", label: "Orders", hint: "Landing page orders" },
];

// Keep for backwards compatibility — some pages still import this
export const adminRoutes = [...pipelineRoutes, ...outreachRoutes, ...opsRoutes];
