import React, { useState, useEffect } from "react";
import { scansAPI, createWebSocket } from "../utils/api";
import { X, AlertTriangle, Shield, Key, Package } from "lucide-react";

const SEVERITY_STYLES = {
  critical: { bg: "#fee2e2", color: "#dc2626", label: "Critical" },
  high: { bg: "#ffedd5", color: "#ea580c", label: "High" },
  medium: { bg: "#fef9c3", color: "#ca8a04", label: "Medium" },
  low: { bg: "#dcfce7", color: "#16a34a", label: "Low" },
};

const AGENT_ICON = {
  sast: <Shield size={14} />,
  secrets: <Key size={14} />,
  deps: <Package size={14} />,
};

export default function FindingsDrawer({ scanId, onClose }) {
  const [findings, setFindings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const [wsStatus, setWsStatus] = useState("");
  const [expanded, setExpanded] = useState(null);

  useEffect(() => {
    scansAPI.getFindings(scanId).then((res) => {
      setFindings(res.data);
      setLoading(false);
    });

    const ws = createWebSocket(scanId);
    ws.onopen = () => setWsStatus("live");
    ws.onmessage = (e) => {
      const data = JSON.parse(e.data);
      if (data.status === "completed") {
        scansAPI.getFindings(scanId).then((res) => setFindings(res.data));
        setWsStatus("done");
      }
    };
    ws.onclose = () => setWsStatus("");
    return () => ws.close();
  }, [scanId]);

  const filtered = filter === "all" ? findings : findings.filter((f) => f.severity === filter);

  return (
    <div style={{
      position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)",
      zIndex: 1000, display: "flex", justifyContent: "flex-end"
    }}>
      <div style={{
        width: 640, background: "#fff", height: "100%",
        overflowY: "auto", boxShadow: "-4px 0 24px rgba(0,0,0,0.1)"
      }}>
        {/* Header */}
        <div style={{
          padding: "20px 24px", borderBottom: "1px solid #e5e7eb",
          position: "sticky", top: 0, background: "#fff", zIndex: 1
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700 }}>
                Findings — Scan #{scanId}
              </h2>
              {wsStatus === "live" && (
                <span style={{ fontSize: 12, color: "#22c55e", display: "flex", alignItems: "center", gap: 4 }}>
                  <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#22c55e", display: "inline-block" }} />
                  Live
                </span>
              )}
            </div>
            <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer" }}>
              <X size={20} />
            </button>
          </div>

          {/* Severity Filter */}
          <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
            {["all", "critical", "high", "medium", "low"].map((s) => (
              <button
                key={s}
                onClick={() => setFilter(s)}
                style={{
                  padding: "4px 12px", borderRadius: 20, border: "none", cursor: "pointer",
                  fontSize: 12, fontWeight: 500,
                  background: filter === s ? "#6366f1" : "#f3f4f6",
                  color: filter === s ? "#fff" : "#374151"
                }}
              >
                {s.charAt(0).toUpperCase() + s.slice(1)}
                {s !== "all" && ` (${findings.filter(f => f.severity === s).length})`}
              </button>
            ))}
          </div>
        </div>

        {/* Findings List */}
        <div style={{ padding: 24 }}>
          {loading && <p style={{ color: "#6b7280" }}>Loading findings...</p>}
          {!loading && filtered.length === 0 && (
            <div style={{ textAlign: "center", padding: "48px 0", color: "#6b7280" }}>
              <Shield size={40} color="#22c55e" />
              <p>No findings for this filter.</p>
            </div>
          )}

          {filtered.map((finding) => {
            const style = SEVERITY_STYLES[finding.severity] || SEVERITY_STYLES.low;
            const isExpanded = expanded === finding.id;

            return (
              <div
                key={finding.id}
                style={{
                  border: "1px solid #e5e7eb", borderRadius: 10, marginBottom: 12,
                  overflow: "hidden", cursor: "pointer"
                }}
                onClick={() => setExpanded(isExpanded ? null : finding.id)}
              >
                {/* Finding Header */}
                <div style={{ padding: "14px 16px", background: "#fafafa" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                        <span style={{
                          background: style.bg, color: style.color,
                          padding: "2px 8px", borderRadius: 4, fontSize: 11, fontWeight: 600
                        }}>
                          {style.label}
                        </span>
                        <span style={{
                          display: "flex", alignItems: "center", gap: 4,
                          fontSize: 11, color: "#6b7280",
                          background: "#f3f4f6", padding: "2px 8px", borderRadius: 4
                        }}>
                          {AGENT_ICON[finding.agent]} {finding.agent?.toUpperCase()}
                        </span>
                        {finding.cwe_id && (
                          <span style={{ fontSize: 11, color: "#6b7280" }}>{finding.cwe_id}</span>
                        )}
                      </div>
                      <p style={{ margin: 0, fontWeight: 600, fontSize: 14 }}>{finding.title}</p>
                      {finding.file_path && (
                        <p style={{ margin: "4px 0 0", fontSize: 12, color: "#6b7280", fontFamily: "monospace" }}>
                          {finding.file_path}{finding.line_start ? `:${finding.line_start}` : ""}
                        </p>
                      )}
                    </div>
                    <span style={{ color: "#9ca3af", fontSize: 18 }}>{isExpanded ? "▲" : "▼"}</span>
                  </div>
                </div>

                {/* Expanded Details */}
                {isExpanded && (
                  <div style={{ padding: 16, borderTop: "1px solid #e5e7eb" }}>
                    {finding.ai_explanation && (
                      <div style={{ marginBottom: 12 }}>
                        <p style={{ margin: "0 0 6px", fontSize: 12, fontWeight: 600, color: "#6366f1" }}>
                          🤖 AI Explanation (LLaMA 3)
                        </p>
                        <p style={{ margin: 0, fontSize: 13, color: "#374151", lineHeight: 1.6 }}>
                          {finding.ai_explanation}
                        </p>
                      </div>
                    )}

                    {finding.code_snippet && (
                      <div style={{ marginBottom: 12 }}>
                        <p style={{ margin: "0 0 6px", fontSize: 12, fontWeight: 600, color: "#374151" }}>Code</p>
                        <pre style={{
                          background: "#1e1e1e", color: "#d4d4d4", padding: 12,
                          borderRadius: 6, fontSize: 12, overflowX: "auto", margin: 0
                        }}>
                          {finding.code_snippet}
                        </pre>
                      </div>
                    )}

                    {finding.fix_suggestion && (
                      <div style={{
                        background: "#f0fdf4", border: "1px solid #bbf7d0",
                        borderRadius: 8, padding: 12
                      }}>
                        <p style={{ margin: "0 0 6px", fontSize: 12, fontWeight: 600, color: "#16a34a" }}>
                          ✅ Fix Suggestion
                        </p>
                        <p style={{ margin: 0, fontSize: 13, color: "#374151" }}>{finding.fix_suggestion}</p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
