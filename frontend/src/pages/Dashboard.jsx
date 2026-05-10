import React, { useState, useEffect } from "react";
import { scansAPI } from "../utils/api";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar
} from "recharts";
import { Shield, AlertTriangle, GitPullRequest, Database, Clock, CheckCircle, XCircle, Loader } from "lucide-react";
import ManualScanModal from "../components/ManualScanModal";
import FindingsDrawer from "../components/FindingsDrawer";

const SEVERITY_COLORS = {
  critical: "#ef4444",
  high: "#f97316",
  medium: "#eab308",
  low: "#22c55e",
};

const STATUS_ICON = {
  completed: <CheckCircle size={16} color="#22c55e" />,
  running: <Loader size={16} color="#3b82f6" className="spin" />,
  pending: <Clock size={16} color="#eab308" />,
  failed: <XCircle size={16} color="#ef4444" />,
};

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [scans, setScans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showScanModal, setShowScanModal] = useState(false);
  const [selectedScanId, setSelectedScanId] = useState(null);

  const fetchData = async () => {
    try {
      const [statsRes, scansRes] = await Promise.all([
        scansAPI.getStats(),
        scansAPI.list(),
      ]);
      setStats(statsRes.data);
      setScans(scansRes.data.scans);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 15000); // Refresh every 15s
    return () => clearInterval(interval);
  }, []);

  if (loading) return (
    <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "60vh" }}>
      <div style={{ textAlign: "center" }}>
        <Shield size={48} color="#6366f1" />
        <p style={{ marginTop: 12, color: "#6b7280" }}>Loading dashboard...</p>
      </div>
    </div>
  );

  return (
    <div style={{ padding: "24px", maxWidth: 1200, margin: "0 auto" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 24, fontWeight: 700 }}>Security Dashboard</h1>
          <p style={{ margin: "4px 0 0", color: "#6b7280", fontSize: 14 }}>
            Powered by LLaMA 3 · LangGraph · Semgrep · Bandit
          </p>
        </div>
        <button
          onClick={() => setShowScanModal(true)}
          style={{
            background: "#6366f1", color: "#fff", border: "none",
            padding: "10px 20px", borderRadius: 8, cursor: "pointer",
            fontSize: 14, fontWeight: 600, display: "flex", alignItems: "center", gap: 8
          }}
        >
          + Manual Scan
        </button>
      </div>

      {/* Stat Cards */}
      {stats && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 24 }}>
          {[
            { label: "Total Scans", value: stats.total_scans, icon: <GitPullRequest size={20} />, color: "#6366f1" },
            { label: "Total Findings", value: stats.total_findings, icon: <AlertTriangle size={20} />, color: "#f97316" },
            { label: "Critical Issues", value: stats.critical_findings, icon: <Shield size={20} />, color: "#ef4444" },
            { label: "Repos Scanned", value: stats.repos_scanned, icon: <Database size={20} />, color: "#22c55e" },
          ].map((card) => (
            <div key={card.label} style={{
              background: "#fff", border: "1px solid #e5e7eb", borderRadius: 12,
              padding: "20px", boxShadow: "0 1px 3px rgba(0,0,0,0.06)"
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                <div>
                  <p style={{ margin: 0, color: "#6b7280", fontSize: 13 }}>{card.label}</p>
                  <p style={{ margin: "8px 0 0", fontSize: 28, fontWeight: 700, color: "#111" }}>{card.value}</p>
                </div>
                <div style={{
                  background: card.color + "15", color: card.color,
                  padding: 10, borderRadius: 8
                }}>
                  {card.icon}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Charts */}
      {stats?.trend?.length > 0 && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 24 }}>
          <div style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: 12, padding: 20 }}>
            <h3 style={{ margin: "0 0 16px", fontSize: 15, fontWeight: 600 }}>Findings Trend</h3>
            <ResponsiveContainer width="100%" height={180}>
              <AreaChart data={stats.trend}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
                <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Area type="monotone" dataKey="findings" stroke="#6366f1" fill="#eef2ff" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <div style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: 12, padding: 20 }}>
            <h3 style={{ margin: "0 0 16px", fontSize: 15, fontWeight: 600 }}>Critical vs Total</h3>
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={stats.trend}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
                <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Bar dataKey="findings" fill="#e0e7ff" radius={[4, 4, 0, 0]} />
                <Bar dataKey="critical" fill="#ef4444" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Scans Table */}
      <div style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: 12, overflow: "hidden" }}>
        <div style={{ padding: "16px 20px", borderBottom: "1px solid #e5e7eb" }}>
          <h3 style={{ margin: 0, fontSize: 15, fontWeight: 600 }}>Recent Scans</h3>
        </div>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ background: "#f9fafb" }}>
              {["Repository", "PR", "Branch", "Status", "Findings", "Time", ""].map(h => (
                <th key={h} style={{ padding: "10px 16px", textAlign: "left", fontSize: 12, color: "#6b7280", fontWeight: 600 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {scans.map((scan) => (
              <tr key={scan.id} style={{ borderTop: "1px solid #f3f4f6" }}>
                <td style={{ padding: "12px 16px", fontSize: 14, fontWeight: 500 }}>{scan.repo}</td>
                <td style={{ padding: "12px 16px", fontSize: 13, color: "#6b7280" }}>
                  {scan.pr_number > 0 ? `#${scan.pr_number}` : "Manual"}
                </td>
                <td style={{ padding: "12px 16px" }}>
                  <span style={{
                    background: "#f3f4f6", padding: "2px 8px", borderRadius: 4,
                    fontSize: 12, fontFamily: "monospace"
                  }}>{scan.branch}</span>
                </td>
                <td style={{ padding: "12px 16px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}>
                    {STATUS_ICON[scan.status]}
                    {scan.status}
                  </div>
                </td>
                <td style={{ padding: "12px 16px" }}>
                  <div style={{ display: "flex", gap: 4 }}>
                    {scan.critical_count > 0 && (
                      <span style={{ background: "#fee2e2", color: "#dc2626", padding: "2px 6px", borderRadius: 4, fontSize: 11, fontWeight: 600 }}>
                        {scan.critical_count} C
                      </span>
                    )}
                    {scan.high_count > 0 && (
                      <span style={{ background: "#ffedd5", color: "#ea580c", padding: "2px 6px", borderRadius: 4, fontSize: 11, fontWeight: 600 }}>
                        {scan.high_count} H
                      </span>
                    )}
                    {scan.medium_count > 0 && (
                      <span style={{ background: "#fef9c3", color: "#ca8a04", padding: "2px 6px", borderRadius: 4, fontSize: 11, fontWeight: 600 }}>
                        {scan.medium_count} M
                      </span>
                    )}
                    {scan.total_findings === 0 && <span style={{ color: "#22c55e", fontSize: 12 }}>✓ Clean</span>}
                  </div>
                </td>
                <td style={{ padding: "12px 16px", fontSize: 12, color: "#9ca3af" }}>
                  {scan.started_at ? new Date(scan.started_at).toLocaleString() : "-"}
                </td>
                <td style={{ padding: "12px 16px" }}>
                  <button
                    onClick={() => setSelectedScanId(scan.id)}
                    style={{
                      background: "none", border: "1px solid #e5e7eb", padding: "4px 12px",
                      borderRadius: 6, cursor: "pointer", fontSize: 12, color: "#374151"
                    }}
                  >
                    View
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showScanModal && (
        <ManualScanModal
          onClose={() => setShowScanModal(false)}
          onSuccess={() => { setShowScanModal(false); fetchData(); }}
        />
      )}

      {selectedScanId && (
        <FindingsDrawer
          scanId={selectedScanId}
          onClose={() => setSelectedScanId(null)}
        />
      )}
    </div>
  );
}
