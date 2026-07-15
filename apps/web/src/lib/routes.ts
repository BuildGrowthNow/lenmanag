export const adminRoutes = [
  { href: "/nsa", label: "Dashboard", hint: "Overview" },
  { href: "/nsa/leads", label: "Leads", hint: "Import and track" },
  { href: "/nsa/sites", label: "Websites", hint: "Generated previews" },
  { href: "/nsa/messages", label: "Messages", hint: "Drafts and ready states" },
  { href: "/nsa/analytics", label: "Analytics", hint: "Visits and clicks" },
  { href: "/nsa/review", label: "Review", hint: "QA queue" },
  { href: "/nsa/scale", label: "Scale", hint: "Queues & retries" }
];

export const workspaceRoutes = [
  { href: "/nsa/leads/[id]", label: "Lead detail" },
  { href: "/nsa/sites/[id]", label: "Site detail" },
  { href: "/nsa/sites/[id]/brief", label: "Site brief" },
  { href: "/nsa/sites/[id]/edit", label: "Edit workspace" },
  { href: "/sites/[slug]", label: "Public preview" }
];
