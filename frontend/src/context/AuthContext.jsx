import { createContext, useContext, useMemo, useState } from "react";
import { clearAuthStorage, readJson, writeJson } from "../utils/storage.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem("auth_token") || "");
  const [user, setUser] = useState(() => readJson("login_user", null));

  const value = useMemo(() => ({
    token,
    user,
    signIn(data, fallbackRole) {
      const nextUser = data?.user || null;
      const nextToken = data?.token || "";
      if (nextUser) writeJson("login_user", nextUser);
      if (nextToken) localStorage.setItem("auth_token", nextToken);
      if (fallbackRole) localStorage.setItem("login_role", fallbackRole);
      setUser(nextUser);
      setToken(nextToken);
    },
    signOut() {
      clearAuthStorage();
      setUser(null);
      setToken("");
    }
  }), [token, user]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
