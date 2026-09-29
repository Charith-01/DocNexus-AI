import { useCallback, useEffect, useState } from "react";

import { api, session } from "../services/api";
import type { User } from "../types/api";

export function useSession() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(Boolean(session.getToken()));

  const logout = useCallback(() => {
    session.clear();
    setUser(null);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const token = await api.login(email, password);
    session.setToken(token.access_token);
    const profile = await api.me();
    setUser(profile);
  }, []);

  useEffect(() => {
    const restore = async () => {
      if (!session.getToken()) {
        setLoading(false);
        return;
      }
      try {
        setUser(await api.me());
      } catch {
        logout();
      } finally {
        setLoading(false);
      }
    };
    void restore();

    window.addEventListener("docnexus:auth-expired", logout);
    return () => window.removeEventListener("docnexus:auth-expired", logout);
  }, [logout]);

  return { user, loading, login, logout };
}
