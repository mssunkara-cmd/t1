import { createContext, type ReactNode, useContext, useMemo, useState } from "react";

import * as authApi from "../api/auth";
import type { AuthTokens, AuthUser } from "../types/models";

type AuthContextValue = {
  user: AuthUser | null;
  accessToken: string | null;
  refreshToken: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (
    email: string,
    password: string,
    role: "buyer" | "seller",
    profile?: Record<string, string | number>
  ) => Promise<void>;
  bootstrapAdmin: (
    email: string,
    password: string,
    profile?: Record<string, string | number>
  ) => Promise<void>;
  updateProfile: (profile: Record<string, string | number>) => Promise<void>;
  logout: () => void;
  hasRole: (role: string) => boolean;
};

const AuthContext = createContext<AuthContextValue | null>(null);

const STORAGE_KEY = "marketplace_auth";

function readInitialState(): AuthTokens | null {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) {
    return null;
  }
  try {
    return JSON.parse(raw) as AuthTokens;
  } catch {
    localStorage.removeItem(STORAGE_KEY);
    return null;
  }
}

function writeState(state: AuthTokens | null) {
  if (state) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } else {
    localStorage.removeItem(STORAGE_KEY);
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const initial = readInitialState();
  const [user, setUser] = useState<AuthUser | null>(initial?.user ?? null);
  const [accessToken, setAccessToken] = useState<string | null>(initial?.access_token ?? null);
  const [refreshToken, setRefreshToken] = useState<string | null>(initial?.refresh_token ?? null);

  const setSession = (session: AuthTokens | null) => {
    setUser(session?.user ?? null);
    setAccessToken(session?.access_token ?? null);
    setRefreshToken(session?.refresh_token ?? null);
    writeState(session);
  };

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      accessToken,
      refreshToken,
      login: async (email, password) => {
        const session = await authApi.login(email, password);
        setSession(session);
      },
      register: async (email, password, role, profile) => {
        const session = await authApi.register(email, password, role, profile);
        setSession(session);
      },
      bootstrapAdmin: async (email, password, profile) => {
        const session = await authApi.bootstrapAdmin(email, password, profile);
        setSession(session);
      },
      updateProfile: async (profile) => {
        if (!accessToken) {
          throw new Error("Not authenticated");
        }
        const updatedUser = await authApi.updateMyProfile(accessToken, profile);
        setUser(updatedUser);
        const persisted = readInitialState();
        if (persisted) {
          writeState({ ...persisted, user: updatedUser });
        }
      },
      logout: () => setSession(null),
      hasRole: (role: string) => Boolean(user?.roles.includes(role))
    }),
    [user, accessToken, refreshToken]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
