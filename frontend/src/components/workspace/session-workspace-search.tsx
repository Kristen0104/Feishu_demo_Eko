"use client";

import { usePathname } from "next/navigation";
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

type SessionWorkspaceSearchValue = {
  query: string;
  setQuery: (q: string) => void;
};

const SessionWorkspaceSearchContext = createContext<SessionWorkspaceSearchValue | null>(null);

export function SessionWorkspaceSearchProvider({ children }: { children: ReactNode }) {
  const [query, setQuery] = useState("");
  const pathname = usePathname() ?? "";
  useEffect(() => {
    const timer = window.setTimeout(() => {
      setQuery("");
    }, 0);
    return () => window.clearTimeout(timer);
  }, [pathname]);
  const value = useMemo(() => ({ query, setQuery }), [query]);
  return <SessionWorkspaceSearchContext.Provider value={value}>{children}</SessionWorkspaceSearchContext.Provider>;
}

/** Used by session detail workspace and top bar; safe default when called outside provider. */
export function useSessionWorkspaceSearch(): SessionWorkspaceSearchValue {
  const ctx = useContext(SessionWorkspaceSearchContext);
  return ctx ?? { query: "", setQuery: () => {} };
}
