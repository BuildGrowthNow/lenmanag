"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { pipelineRoutes, outreachRoutes, opsRoutes } from "@/lib/routes";
import { cn } from "@/lib/utils";

type NavItem = { href: string; label: string; hint?: string; badge?: number };

function NavLink({ item, active }: { item: NavItem; active: boolean }) {
  return (
    <li>
      <Link
        className={cn(
          "flex items-center justify-between rounded-xl px-3 py-2 text-sm transition",
          active
            ? "bg-accent/15 text-accent font-medium"
            : "text-text hover:bg-white/5"
        )}
        href={item.href}
      >
        <span>{item.label}</span>
        <span className="flex items-center gap-2">
          {item.badge != null && item.badge > 0 ? (
            <span className="rounded-full bg-accent/20 px-1.5 py-0.5 text-[10px] font-semibold text-accent">
              {item.badge}
            </span>
          ) : null}
          {item.hint ? (
            <span className="text-xs text-muted">{item.hint}</span>
          ) : null}
        </span>
      </Link>
    </li>
  );
}

function NavSection({
  label,
  items,
  pathname,
  collapsible = false,
  defaultOpen = true,
}: {
  label: string;
  items: NavItem[];
  pathname: string;
  collapsible?: boolean;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div>
      <button
        type="button"
        onClick={() => collapsible && setOpen((o) => !o)}
        className={cn(
          "mb-2 flex w-full items-center gap-1 text-[11px] uppercase tracking-[0.28em] text-muted",
          collapsible && "cursor-pointer hover:text-text"
        )}
      >
        {label}
        {collapsible ? (
          open ? (
            <ChevronDown className="ml-auto h-3 w-3" />
          ) : (
            <ChevronRight className="ml-auto h-3 w-3" />
          )
        ) : null}
      </button>
      {open ? (
        <ul className="space-y-0.5">
          {items.map((item) => (
            <NavLink
              key={item.href}
              item={item}
              active={
                item.href === "/app"
                  ? pathname === "/app"
                  : pathname.startsWith(item.href)
              }
            />
          ))}
        </ul>
      ) : null}
    </div>
  );
}

export function Sidebar() {
  const pathname = usePathname();

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
        <NavSection label="Pipeline" items={pipelineRoutes} pathname={pathname} />
        <NavSection label="Outreach" items={outreachRoutes} pathname={pathname} />
        <NavSection
          label="Ops"
          items={opsRoutes}
          pathname={pathname}
          collapsible
          defaultOpen={false}
        />
      </nav>
    </aside>
  );
}
