import { AppShell } from "@/components/shell/app-shell";
import { AuthProvider } from "@/lib/auth-context";

export const dynamic = "force-dynamic";

export default function NSALayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <AuthProvider>
      <AppShell>{children}</AppShell>
    </AuthProvider>
  );
}
