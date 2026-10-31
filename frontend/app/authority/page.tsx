"use client";

/**
 * Authority Center for ALFRED AI.
 * 
 * Displays:
 * - Pending Human Approvals (L2 sensitive actions)
 * - Active Temporary Capabilities (HMAC-SHA256 signed, short-lived tokens)
 * - Approval Resolution History
 * - Hard-denied Protected Resources (L3)
 */

import React, { useState, useEffect } from "react";
import { Navbar } from "@/components/Navbar";
import {
  KeyRound,
  CheckCircle,
  XCircle,
  Clock,
  ShieldAlert,
  Lock,
  FileCheck,
  AlertTriangle,
} from "lucide-react";
import { api } from "@/lib/api";
import { ApprovalItem, CapabilityRecord } from "@/lib/types";

export default function AuthorityCenterPage() {
  const [pendingApprovals, setPendingApprovals] = useState<ApprovalItem[]>([]);
  const [approvalHistory, setApprovalHistory] = useState<any[]>([]);
  const [capabilities, setCapabilities] = useState<CapabilityRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  const loadData = async () => {
    try {
      const data = await api.getAuthorityData();
      setPendingApprovals(data.pending_approvals || []);
      setApprovalHistory(data.approval_history || []);
      setCapabilities(data.capabilities || []);
    } catch (err) {
      console.error("Failed to fetch authority data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 4000);
    return () => clearInterval(interval);
  }, []);

  const handleDecision = async (taskId: string, approved: boolean) => {
    try {
      await api.decideApproval(taskId, approved);
      loadData();
    } catch (err: any) {
      alert(`Decision error: ${err.message}`);
    }
  };

  return (
    <>
      <Navbar title="Authority Center & Capability Manager" />
      <main className="p-8 space-y-8 flex-1">
        {/* Pending Approvals Section (Top) */}
        <div className="bg-cyber-card border border-cyber-border rounded-xl p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-cyber-border/70 pb-3">
            <div className="flex items-center gap-2 font-mono text-xs font-bold uppercase text-cyber-warning">
              <AlertTriangle className="w-4 h-4" />
              <span>Pending Human Approvals ({pendingApprovals.length})</span>
            </div>
            <span className="text-[11px] font-mono text-cyber-textMuted">
              Requires Operator Cryptographic Signature
            </span>
          </div>

          <div className="space-y-4">
            {loading ? (
              <div className="py-8 text-center text-xs text-cyber-textMuted font-mono">Loading approval queue...</div>
            ) : pendingApprovals.length > 0 ? (
              pendingApprovals.map((appr) => (
                <div
                  key={appr.id}
                  className="p-5 bg-cyber-bg border border-cyber-warning/40 rounded-xl space-y-3"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="flex items-center gap-2 font-mono text-xs font-bold text-cyber-textPrimary">
                        <span className="text-cyber-warning">[{appr.tool_name}]</span>
                        <span>{appr.operation}</span>
                      </div>
                      <p className="text-xs text-cyber-textSecondary mt-1">{appr.explanation}</p>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <button
                        onClick={() => handleDecision(appr.task_id, true)}
                        className="px-3.5 py-1.5 rounded-lg bg-cyber-permitted hover:bg-cyber-permitted/90 text-white font-mono text-xs font-semibold flex items-center gap-1.5 shadow-sm"
                      >
                        <CheckCircle className="w-3.5 h-3.5" />
                        APPROVE
                      </button>
                      <button
                        onClick={() => handleDecision(appr.task_id, false)}
                        className="px-3.5 py-1.5 rounded-lg bg-cyber-blocked/20 hover:bg-cyber-blocked/30 border border-cyber-blocked/40 text-cyber-blocked font-mono text-xs font-semibold flex items-center gap-1.5"
                      >
                        <XCircle className="w-3.5 h-3.5" />
                        REJECT
                      </button>
                    </div>
                  </div>

                  {/* Immutable Parameters Box */}
                  <div className="p-3 bg-cyber-card rounded border border-cyber-border/70 font-mono text-[11px] text-cyber-textSecondary overflow-x-auto">
                    <span className="text-cyber-textMuted">Immutable Parameters: </span>
                    {JSON.stringify(appr.parameters, null, 2)}
                  </div>
                </div>
              ))
            ) : (
              <div className="py-8 text-center text-xs text-cyber-textMuted font-mono">
                No approvals currently pending.
              </div>
            )}
          </div>
        </div>

        {/* Bottom Section: Active Capabilities & Approval History */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Active Capabilities */}
          <div className="bg-cyber-card border border-cyber-border rounded-xl p-6 space-y-4 shadow-sm">
            <div className="flex items-center gap-2 border-b border-cyber-border/70 pb-3 font-mono text-xs font-bold uppercase text-cyber-accent">
              <KeyRound className="w-4 h-4" />
              <span>Cryptographic Capabilities ({capabilities.length})</span>
            </div>

            <div className="space-y-2.5 max-h-[380px] overflow-y-auto pr-1">
              {capabilities.length > 0 ? (
                capabilities.map((cap) => (
                  <div
                    key={cap.id}
                    className="p-3 bg-cyber-bg/70 border border-cyber-border rounded-lg text-xs font-mono space-y-1"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-cyber-accent font-semibold">{cap.authorized_tool}:{cap.exact_operation}</span>
                      <span className="text-[10px] text-cyber-textMuted">
                        Scope: {cap.resource_scope}
                      </span>
                    </div>
                    <div className="text-[10px] text-cyber-textMuted flex items-center justify-between pt-1">
                      <span>ID: {cap.id.slice(0, 8)}...</span>
                      <span className="text-cyber-permitted font-semibold">HMAC-SHA256 SIGNED</span>
                    </div>
                  </div>
                ))
              ) : (
                <div className="py-8 text-center text-xs text-cyber-textMuted font-mono">
                  No capabilities currently active.
                </div>
              )}
            </div>
          </div>

          {/* Approval History */}
          <div className="bg-cyber-card border border-cyber-border rounded-xl p-6 space-y-4 shadow-sm">
            <div className="flex items-center gap-2 border-b border-cyber-border/70 pb-3 font-mono text-xs font-bold uppercase text-cyber-textPrimary">
              <FileCheck className="w-4 h-4 text-cyber-permitted" />
              <span>Authorization History</span>
            </div>

            <div className="space-y-2.5 max-h-[380px] overflow-y-auto pr-1">
              {approvalHistory.length > 0 ? (
                approvalHistory.map((h) => (
                  <div
                    key={h.id}
                    className="p-3 bg-cyber-bg/60 border border-cyber-border rounded-lg text-xs font-mono flex items-center justify-between"
                  >
                    <div>
                      <div className="text-cyber-textPrimary font-semibold">
                        {h.tool_name}:{h.operation}
                      </div>
                      <div className="text-[10px] text-cyber-textMuted mt-0.5">
                        Decided by {h.decided_by || "OPERATOR"}
                      </div>
                    </div>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        h.status === "APPROVED"
                          ? "bg-cyber-permitted/10 text-cyber-permitted border border-cyber-permitted/30"
                          : "bg-cyber-blocked/10 text-cyber-blocked border border-cyber-blocked/30"
                      }`}
                    >
                      {h.status}
                    </span>
                  </div>
                ))
              ) : (
                <div className="py-8 text-center text-xs text-cyber-textMuted font-mono">
                  No past authorization decisions recorded.
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
    </>
  );
}
