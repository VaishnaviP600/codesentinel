import React from "react";
import { useAuth } from "../hooks/useAuth";
import { Shield, LogOut, User } from "lucide-react";

export default function Navbar() {
  const { user, logout } = useAuth();

  return (
    <nav style={{
      background: "#fff", borderBottom: "1px solid #e5e7eb",
      padding: "0 24px", height: 56,
      display: "flex", alignItems: "center", justifyContent: "space-between",
      position: "sticky", top: 0, zIndex: 100,
      boxShadow: "0 1px 3px rgba(0,0,0,0.05)"
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <Shield size={22} color="#6366f1" />
        <span style={{ fontWeight: 700, fontSize: 16, color: "#111" }}>CodeSentinel</span>
        <span style={{
          background: "#eef2ff", color: "#6366f1",
          fontSize: 10, fontWeight: 600, padding: "2px 8px",
          borderRadius: 20, marginLeft: 4
        }}>
          AI-Powered
        </span>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <div style={{
          display: "flex", alignItems: "center", gap: 6,
          padding: "6px 12px", background: "#f9fafb",
          borderRadius: 8, fontSize: 13, color: "#374151"
        }}>
          <User size={14} />
          {user?.username}
        </div>
        <button
          onClick={logout}
          style={{
            display: "flex", alignItems: "center", gap: 6,
            padding: "6px 12px", background: "none",
            border: "1px solid #e5e7eb", borderRadius: 8,
            cursor: "pointer", fontSize: 13, color: "#6b7280"
          }}
        >
          <LogOut size={14} />
          Logout
        </button>
      </div>
    </nav>
  );
}
