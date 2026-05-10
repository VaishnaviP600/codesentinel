import React, { createContext, useContext, useState, useEffect } from "react";
import { authAPI } from "../utils/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("token");
    const username = localStorage.getItem("username");
    if (token && username) setUser({ username, token });
    setLoading(false);
  }, []);

  const login = async (username, password) => {
    const res = await authAPI.login(username, password);
    localStorage.setItem("token", res.data.access_token);
    localStorage.setItem("username", res.data.username);
    setUser({ username: res.data.username, token: res.data.access_token });
  };

  const register = async (username, email, password) => {
    const res = await authAPI.register(username, email, password);
    localStorage.setItem("token", res.data.access_token);
    localStorage.setItem("username", res.data.username);
    setUser({ username: res.data.username, token: res.data.access_token });
  };

  const logout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("username");
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login, register, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
