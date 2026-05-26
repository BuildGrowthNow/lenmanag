import { Badge } from "@/components/ui/badge";

export function Topbar() {
  return (
    <div className="flex items-center justify-between border-b border-line bg-panel/60 px-6 py-4 backdrop-blur">
      <div>
        <div className="text-xs uppercase tracking-[0.3em] text-muted">Admin-only control plane</div>
        <div className="mt-1 font-medium text-text">LenQuant operator workspace</div>
      </div>
      <div className="flex items-center gap-2">
        <Badge>Allowlist auth</Badge>
        <Badge className="bg-success/15 text-success">Phase 1 shell</Badge>
      </div>
    </div>
  );
}

