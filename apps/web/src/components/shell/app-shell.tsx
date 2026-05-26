import { ReactNode } from "react";

import { Sidebar } from "@/components/shell/sidebar";
import { Topbar } from "@/components/shell/topbar";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(255,255,255,0.05),_transparent_26%),linear-gradient(180deg,_#0c1016_0%,_#070a0f_100%)] text-text">
      <div className="flex min-h-screen">
        <div className="hidden w-80 shrink-0 lg:block">
          <Sidebar />
        </div>
        <div className="flex min-h-screen flex-1 flex-col">
          <Topbar />
          <main className="flex-1 px-4 py-5 lg:px-8">{children}</main>
        </div>
      </div>
    </div>
  );
}

