import { AppShell } from "@/components/shell/app-shell";

export const dynamic = "force-dynamic";

export default function NSALayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <AppShell>{children}</AppShell>;
}
