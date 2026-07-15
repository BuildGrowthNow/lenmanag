"use client";

import { useState } from "react";
import { Diff } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { OverrideDiff } from "@/lib/types";

type OverrideDiffBadgeProps = {
  diff: OverrideDiff;
  onDisable?: (overrideId: string) => void;
};

export function OverrideDiffBadge({ diff, onDisable }: OverrideDiffBadgeProps) {
  const [showTooltip, setShowTooltip] = useState(false);

  const diffTypeColor = {
    changed: "border-amber-500/40 bg-amber-500/10 text-amber-100",
    added: "border-emerald-500/40 bg-emerald-500/10 text-emerald-100",
    removed: "border-rose-500/40 bg-rose-500/10 text-rose-100",
  }[diff.diffType];

  return (
    <div className="relative inline-block">
      <button
        type="button"
        onClick={() => setShowTooltip(!showTooltip)}
        className="cursor-pointer"
      >
        <Badge className={diffTypeColor}>
          <Diff className="mr-1 h-3 w-3" />
          {diff.diffType}
        </Badge>
      </button>

      {showTooltip && (
        <div className="absolute z-50 mt-2 w-80 rounded-2xl border border-line bg-panel-2 p-4 shadow-lg">
          <div className="mb-3 flex items-center justify-between">
            <div className="text-xs uppercase tracking-[0.18em] text-muted">Override diff</div>
            <Button
              variant="ghost"
              className="h-6 px-2 text-xs"
              onClick={() => setShowTooltip(false)}
            >
              Close
            </Button>
          </div>
          <div className="space-y-2 text-sm">
            <div>
              <div className="text-xs uppercase tracking-[0.18em] text-muted">Path</div>
              <div className="mt-1 text-text">{diff.path}</div>
            </div>
            <div>
              <div className="text-xs uppercase tracking-[0.18em] text-muted">Scope</div>
              <div className="mt-1 text-text">{diff.scope}</div>
            </div>
            {diff.previousValue !== null && (
              <div>
                <div className="text-xs uppercase tracking-[0.18em] text-muted">Previous value</div>
                <div className="mt-1 rounded-xl border border-line/50 bg-panel px-3 py-2 text-muted">
                  {String(diff.previousValue)}
                </div>
              </div>
            )}
            <div>
              <div className="text-xs uppercase tracking-[0.18em] text-muted">Current value</div>
              <div className="mt-1 rounded-xl border border-line/50 bg-panel px-3 py-2 text-text">
                {String(diff.currentValue)}
              </div>
            </div>
            {diff.siteCurrentValue !== null && diff.siteCurrentValue !== diff.currentValue && (
              <div>
                <div className="text-xs uppercase tracking-[0.18em] text-muted">Site current value</div>
                <div className="mt-1 rounded-xl border border-line/50 bg-panel px-3 py-2 text-muted">
                  {String(diff.siteCurrentValue)}
                </div>
              </div>
            )}
            {onDisable && (
              <div className="pt-2">
                <Button
                  variant="destructive"
                  className="w-full"
                  onClick={() => {
                    onDisable(diff.overrideId);
                    setShowTooltip(false);
                  }}
                >
                  Disable override
                </Button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
