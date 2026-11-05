"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { login, setUnauthorizedHandler, signup, type SignupBody } from "@/lib/api";
import { clearSession, loadSession, saveSession } from "@/lib/session";
import type { User } from "@/lib/types";

interface AuthValue {
  user: User | null;
  ready: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => void;
  signUp: (body: SignupBody) => Promise<void>;
}

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);

  const signOut = useCallback(() => {
    clearSession();
    setUser(null);
  }, []);

  useEffect(() => {
    const saved = loadSession();
    if (saved) setUser(saved.user);
    setReady(true);
    setUnauthorizedHandler(signOut);
    return () => setUnauthorizedHandler(null);
  }, [signOut]);

  const signIn = useCallback(async (email: string, password: string) => {
    const result = await login(email, password);
    saveSession(result.access_token, result.user);
    setUser(result.user);
  }, []);

  const signUp = useCallback(async (body: SignupBody) => {
    const result = await signup(body);
    saveSession(result.access_token, result.user);
    setUser(result.user);
  }, []);

  const value = useMemo(
    () => ({ user, ready, signIn, signOut, signUp }),
    [user, ready, signIn, signOut, signUp]
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}