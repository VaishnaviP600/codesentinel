import React, { useState } from "react";
import { scansAPI } from "../utils/api";
import { X, Github } from "lucide-react";

export default function ManualScanModal({ onClose, onSuccess }) {
  const [repoUrl, setRepoUrl] = useState("");
  const [branch, setBranch] = useState("main");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleScan = async () => {
    if (!repoUrl) return setError("Please enter a repository URL");
    setError(""); setLoading(true);
    try {
      await scansAPI.manualScan(repoUrl, branch);
      onSuccess();
    } catch (e) {
      setError(e.response?.data?.detail || "Failed to start scan");
    } finally {
      setLoading(false);
    }
  };

  const inputStyle = {
    width: "100%", padding: "10px 14px", border: "1px solid #e5e7eb",
    borderRadius: 8, fontSize: 14, outline: "none", boxSizing: "border-box"
  };

  return (
    <div style={{
      position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)",
      zIndex: 1000, display: "flex", alignItems: "center", justifyContent: "center"
    }}>
      <div style={{
        background: "#fff", borderRadius: 16, padding: 32,
        width: 480, boxShadow: "0 20px 60px rgba(0,0,0,0.15)"
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <Github size={22} color="#6366f1" />
            <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700 }}>Manual Scan</h2>
          </div>
          <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer" }}>
            <X size={20} />
          </button>
        </div>

        <p style={{ margin: "0 0 20px", fontSize: 14, color: "#6b7280" }}>
          Enter a public GitHub repository URL to scan it for security vulnerabilities.
        </p>

        <label style={{ display: "block", marginBottom: 6, fontSize: 13, fontWeight: 500 }}>
          Repository URL
        </label>
        <input
          style={{ ...inputStyle, marginBottom: 16 }}
          placeholder="https://github.com/owner/repo"
          value={repoUrl}
          onChange={(e) => setRepoUrl(e.target.value)}
        />

        <label style={{ display: "block", marginBottom: 6, fontSize: 13, fontWeight: 500 }}>
          Branch
        </label>
        <input
          style={{ ...inputStyle, marginBottom: 24 }}
          placeholder="main"
          value={branch}
          onChange={(e) => setBranch(e.target.value)}
        />

        {error && <p style={{ color: "#ef4444", fontSize: 13, marginBottom: 12 }}>{error}</p>}

        <div style={{ display: "flex", gap: 12 }}>
          <button
            onClick={onClose}
            style={{
              flex: 1, padding: "11px", border: "1px solid #e5e7eb",
              borderRadius: 8, cursor: "pointer", fontSize: 14, background: "#fff"
            }}
          >
            Cancel
          </button>
          <button
            onClick={handleScan}
            disabled={loading}
            style={{
              flex: 1, padding: "11px", background: "#6366f1", color: "#fff",
              border: "none", borderRadius: 8, cursor: "pointer", fontSize: 14,
              fontWeight: 600, opacity: loading ? 0.7 : 1
            }}
          >
            {loading ? "Starting..." : "Start Scan"}
          </button>
        </div>
      </div>
    </div>
  );
}
