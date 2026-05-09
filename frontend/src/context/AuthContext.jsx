import { createContext, useContext, useState, useEffect } from "react";
import { authAPI } from "../services/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem("flaw_user");
    return saved ? JSON.parse(saved) : null;
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("flaw_token");
    if (token) {
      authAPI.me()
        .then((u) => { setUser(u); localStorage.setItem("flaw_user", JSON.stringify(u)); })
        .catch(() => { localStorage.removeItem("flaw_token"); localStorage.removeItem("flaw_user"); setUser(null); })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const login = async (email, password) => {
    const data = await authAPI.login({ email, password });
    localStorage.setItem("flaw_token", data.access_token);
    localStorage.setItem("flaw_user", JSON.stringify(data.user));
    setUser(data.user);
    return data;
  };

  const signup = async (username, email, password) => {
    const data = await authAPI.signup({ username, email, password });
    localStorage.setItem("flaw_token", data.access_token);
    localStorage.setItem("flaw_user", JSON.stringify(data.user));
    setUser(data.user);
    return data;
  };

  const logout = () => {
    localStorage.removeItem("flaw_token");
    localStorage.removeItem("flaw_user");
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
