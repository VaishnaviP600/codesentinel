import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { Shield } from "lucide-react";

export default function Login() {
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({ username: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { login, register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async () => {
    setError(""); setLoading(true);
    try {
      if (mode === "login") {
        await login(form.username, form.password);
      } else {
        await register(form.username, form.email, form.password);
      }
      navigate("/");
    } catch (e) {
      setError(e.response?.data?.detail || "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  const inputStyle = {
    width: "100%", padding: "10px 14px", border: "1px solid #e5e7eb",
    borderRadius: 8, fontSize: 14, outline: "none", boxSizing: "border-box",
    marginBottom: 12
  };

  return (
    <div style={{
      minHeight: "100vh", background: "#f9fafb",
      display: "flex", alignItems: "center", justifyContent: "center"
    }}>
      <div style={{
        background: "#fff", border: "1px solid #e5e7eb", borderRadius: 16,
        padding: 40, width: 380, boxShadow: "0 4px 24px rgba(0,0,0,0.06)"
      }}>
        <div style={{ textAlign: "center", marginBottom: 32 }}>
          <Shield size={40} color="#6366f1" />
          <h1 style={{ margin: "12px 0 4px", fontSize: 22, fontWeight: 700 }}>CodeSentinel</h1>
          <p style={{ margin: 0, color: "#6b7280", fontSize: 14 }}>AI-Powered Security Scanner</p>
        </div>

        <div style={{ display: "flex", marginBottom: 24, background: "#f3f4f6", borderRadius: 8, padding: 4 }}>
          {["login", "register"].map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              style={{
                flex: 1, padding: "8px", border: "none", borderRadius: 6, cursor: "pointer",
                fontSize: 14, fontWeight: 500,
                background: mode === m ? "#fff" : "transparent",
                color: mode === m ? "#111" : "#6b7280",
                boxShadow: mode === m ? "0 1px 3px rgba(0,0,0,0.1)" : "none"
              }}
            >
              {m.charAt(0).toUpperCase() + m.slice(1)}
            </button>
          ))}
        </div>

        <input
          style={inputStyle}
          placeholder="Username"
          value={form.username}
          onChange={(e) => setForm({ ...form, username: e.target.value })}
        />
        {mode === "register" && (
          <input
            style={inputStyle}
            placeholder="Email"
            type="email"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
          />
        )}
        <input
          style={inputStyle}
          placeholder="Password"
          type="password"
          value={form.password}
          onChange={(e) => setForm({ ...form, password: e.target.value })}
          onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
        />

        {error && (
          <p style={{ color: "#ef4444", fontSize: 13, margin: "0 0 12px" }}>{error}</p>
        )}

        <button
          onClick={handleSubmit}
          disabled={loading}
          style={{
            width: "100%", padding: "12px", background: "#6366f1", color: "#fff",
            border: "none", borderRadius: 8, cursor: "pointer", fontSize: 15,
            fontWeight: 600, opacity: loading ? 0.7 : 1
          }}
        >
          {loading ? "Please wait..." : mode === "login" ? "Sign In" : "Create Account"}
        </button>
      </div>
    </div>
  );
}
