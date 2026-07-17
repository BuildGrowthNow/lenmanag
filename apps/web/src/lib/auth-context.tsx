"use client";

import { createContext, useContext, useEffect, useState, ReactNode, useCallback } from "react";
import { useRouter, usePathname } from "next/navigation";

import { getCurrentUser, logout as logoutApi, UserResponse } from "@/lib/api/users";

interface AuthContextValue {
  user: UserResponse | null;
  loading: boolean;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

const PUBLIC_PATHS = ["/login", "/signup", "/forgot-password", "/reset-password", "/verify-email"];

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<UserResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const isPublicPath = PUBLIC_PATHS.some((p) => pathname.startsWith(p));

  const fetchUser = useCallback(async () => {
    try {
      const userData = await getCurrentUser();
      setUser(userData);
    } catch {
      setUser(null);
      if (!isPublicPath && pathname.startsWith("/app")) {
        router.push("/login");
      }
    } finally {
      setLoading(false);
    }
  }, [isPublicPath, pathname, router]);

  useEffect(() => {
    void fetchUser();
  }, [fetchUser]);

  function logout() {
    logoutApi();
    setUser(null);
    router.push("/login");
  }

  async function refreshUser() {
    await fetchUser();
  }

  return (
    <AuthContext.Provider value={{ user, loading, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
