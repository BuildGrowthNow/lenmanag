import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { adminRoutes, workspaceRoutes } from "@/lib/routes";

export function Sidebar() {
  return (
    <aside className="flex h-full flex-col gap-6 border-r border-line bg-panel/80 p-5 backdrop-blur">
      <div className="space-y-2">
        <Badge className="bg-white/6">Operator Workspace</Badge>
        <div>
          <div style={{ fontFamily: "var(--font-heading)" }} className="text-lg font-semibold text-text">
            LenQuant
          </div>
          <div className="text-xs uppercase tracking-[0.24em] text-muted">Website Fabric</div>
        </div>
      </div>
      <Separator />
      <nav className="space-y-6 text-sm">
        <div>
          <div className="mb-3 text-[11px] uppercase tracking-[0.28em] text-muted">Admin</div>
          <ul className="space-y-1">
            {adminRoutes.map((item) => (
              <li key={item.href}>
                <Link className="flex items-center justify-between rounded-xl px-3 py-2 text-text transition hover:bg-white/5" href={item.href}>
                  <span>{item.label}</span>
                  <span className="text-xs text-muted">{item.hint}</span>
                </Link>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <div className="mb-3 text-[11px] uppercase tracking-[0.28em] text-muted">Route map</div>
          <ul className="space-y-1">
            {workspaceRoutes.map((item) => (
              <li key={item.href}>
                <div className="rounded-xl border border-dashed border-line px-3 py-2 text-xs text-muted">{item.href}</div>
              </li>
            ))}
          </ul>
        </div>
      </nav>
      <div className="mt-auto rounded-2xl border border-line bg-shell-radial p-4 text-xs leading-5 text-muted">
        Source of truth lives in lead, brief, generated spec, overrides, and export metadata. Rendered HTML stays derivative.
      </div>
    </aside>
  );
}
