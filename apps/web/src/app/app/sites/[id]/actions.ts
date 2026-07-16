"use server";

import { revalidatePath } from "next/cache";
import { disableSiteOverride as apiDisableSiteOverride } from "@/lib/api/sites";

export async function disableOverrideAction(siteId: string, overrideId: string) {
  await apiDisableSiteOverride(siteId, overrideId);
  revalidatePath(`/app/sites/${siteId}`);
  return { success: true };
}
