"use client";

import { useRouter } from "next/navigation";
import { OverrideDiffBadge } from "./override-diff-badge";
import type { OverrideDiff } from "@/lib/types";

type OverrideDiffBadgeWrapperProps = {
  diff: OverrideDiff;
  siteId: string;
  onDisable: (overrideId: string) => Promise<{ success: boolean }>;
};

export function OverrideDiffBadgeWrapper({ diff, siteId, onDisable }: OverrideDiffBadgeWrapperProps) {
  const router = useRouter();

  const handleDisable = async (overrideId: string) => {
    await onDisable(overrideId);
    router.refresh();
  };

  return <OverrideDiffBadge diff={diff} onDisable={handleDisable} />;
}
