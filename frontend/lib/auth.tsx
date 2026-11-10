"use client";
import { createContext, useContext, useState, type ReactNode } from "react";
import type { User } from "./types";
type Session = { token: string | null; user: User | null; signIn: (token: string, user: User) => void; clear: () => void };
const Context = createContext<Session | null>(null);
export function AuthProvider({ children }: { children: ReactNode }) {
    const [token, setToken] = useState<string | null>(null); const [user, setUser] = useState<User | null>(null);
    return <Context.Provider value={{ token, user, signIn: (value, person) => { setToken(value); setUser(person); }, clear: () => { setToken(null); setUser(null); } }}>{children}</Context.Provider>;
}
export function useAuth() { const context = useContext(Context); if (!context) throw new Error("AuthProvider missing"); return context; }

