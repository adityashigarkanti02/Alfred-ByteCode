"use client";

/**
 * Dashboard View for ALFRED AI.
 * 
 * Aggregates real backend data:
 * - Real-time metrics (Total tasks, completed, blocked injections, pending approvals)
 * - Security posture indicators
 * - Recent agent activity log
 * - Integration connectivity status
 */

import React, { useState, useEffect } from "react";
import { Navbar } from "@/components/Navbar";
import {
  ShieldAlert,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Activity,
  Server,
  Terminal,
  Lock,
  ArrowUpRight,
} from "lucide-react";
import { api } from "@/lib/api";
import { DashboardMetrics, IntegrationStatus } from "@/lib/types";

export default function DashboardPage() {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [integrations, setIntegrations] = useState<IntegrationStatus[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  const loadData = async () => {
    try {
      const [dashData, integData] = await Promise.all([
        api.getDashboardMetrics(),
        api.getIntegrationsStatus(),
      ]);
      setMetrics(dashData);
      setIntegrations(integData);
    } catch (err) {
      console.error("Failed to load dashboard data", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <>
      <Navbar title="System Dashboard & Threat Overview" />
      <main className="p-8 space-y-8 flex-1">
        {/* Metric Cards Row */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
          {/* Total Tasks */}
          <div className="bg-cyber-card border border-cyber-border rounded-xl p-5 shadow-sm relative overflow-hidden">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono text-cyber-textMuted uppercase">Total Tasks</span>
              <Terminal className="w-4 h-4 text-cyber-accent" />
            </div>
            <div className="mt-3 text-3xl font-bold font-mono text-cyber-textPrimary">
              {loading ? "..." : metrics?.total_tasks || 0}
            </div>
            <div className="mt-2 text-[11px] text-cyber-textSecondary flex items-center gap-1 font-mono">
              <span className="text-cyber-accent">Active workflows</span>
            </div>
          </div>

          {/* Completed Tasks */}
          <div className="bg-cyber-card border border-cyber-border rounded-xl p-5 shadow-sm relative overflow-hidden">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono text-cyber-textMuted uppercase">Completed Tasks</span>
              <CheckCircle2 className="w-4 h-4 text-cyber-permitted" />
            </div>
            <div className="mt-3 text-3xl font-bold font-mono text-cyber-permitted">
              {loading ? "..." : metrics?.completed_tasks || 0}
            </div>
            <div className="mt-2 text-[11px] text-cyber-textSecondary flex items-center gap-1 font-mono">
              <span>Verified executions</span>
            </div>
          </div>

          {/* Blocked Attacks */}
          <div className="bg-cyber-card border border-cyber-border rounded-xl p-5 shadow-sm relative overflow-hidden">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono text-cyber-textMuted uppercase">Blocked Injections</span>
              <ShieldAlert className="w-4 h-4 text-cyber-blocked" />
            </div>
            <div className="mt-3 text-3xl font-bold font-mono text-cyber-blocked">
              {loading ? "..." : metrics?.blocked_attacks || 0}
            </div>
            <div className="mt-2 text-[11px] text-cyber-textSecondary flex items-center gap-1 font-mono">
              <span>Neutralized in sandbox</span>
            </div>
          </div>

          {/* Pending Approvals */}
          <div className="bg-cyber-card border border-cyber-border rounded-xl p-5 shadow-sm relative overflow-hidden">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono text-cyber-textMuted uppercase">Pending Approvals</span>
              <AlertTriangle className="w-4 h-4 text-cyber-warning" />
            </div>
            <div className="mt-3 text-3xl font-bold font-mono text-cyber-warning">
              {loading ? "..." : metrics?.pending_approvals || 0}
            </div>
            <div className="mt-2 text-[11px] text-cyber-textSecondary flex items-center gap-1 font-mono">
              <span>L2 Human verification</span>
            </div>
          </div>
        </div>

        {/* Middle Section: Recent Tasks and Security Posture */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Recent Tasks List (2 Columns) */}
          <div className="lg:col-span-2 bg-cyber-card border border-cyber-border rounded-xl p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-cyber-border/70 pb-3">
              <div className="flex items-center gap-2">
                <Activity className="w-4 h-4 text-cyber-accent" />
                <h2 className="text-xs font-mono font-bold uppercase tracking-wider text-cyber-textPrimary">
                  Recent Autonomous Tasks
                </h2>
              </div>
              <a href="/workspace" className="text-xs text-cyber-accent hover:underline flex items-center gap-1">
                Workspace <ArrowUpRight className="w-3.5 h-3.5" />
              </a>
            </div>

            <div className="divide-y divide-cyber-border/50">
              {loading ? (
                <div className="py-8 text-center text-xs text-cyber-textMuted font-mono">Loading active tasks...</div>
              ) : metrics?.recent_tasks && metrics.recent_tasks.length > 0 ? (
                metrics.recent_tasks.map((task) => (
                  <div key={task.id} className="py-3.5 flex items-center justify-between gap-4">
                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-medium text-cyber-textPrimary truncate">{task.prompt}</p>
                      <div className="flex items-center gap-2 mt-1 text-[10px] text-cyber-textMuted font-mono">
                        <Clock className="w-3 h-3" />
                        <span>{new Date(task.created_at).toLocaleTimeString()}</span>
                        <span>•</span>
                        <span>ID: {task.id.slice(0, 8)}</span>
                      </div>
                    </div>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold uppercase tracking-wider border ${
                        task.status === "COMPLETED"
                          ? "bg-cyber-permitted/10 text-cyber-permitted border-cyber-permitted/30"
                          : task.status === "AWAITING_APPROVAL"
                          ? "bg-cyber-warning/10 text-cyber-warning border-cyber-warning/30"
                          : task.status === "BLOCKED_ATTACK"
                          ? "bg-cyber-blocked/10 text-cyber-blocked border-cyber-blocked/30"
                          : "bg-cyber-accent/10 text-cyber-accent border-cyber-accent/30"
                      }`}
                    >
                      {task.status}
                    </span>
                  </div>
                ))
              ) : (
                <div className="py-8 text-center text-xs text-cyber-textMuted font-mono">
                  No tasks executed yet. Open the Agent Workspace to submit instructions.
                </div>
              )}
            </div>
          </div>

          {/* Integrations Health Card (1 Column) */}
          <div className="bg-cyber-card border border-cyber-border rounded-xl p-6 space-y-4">
            <div className="flex items-center gap-2 border-b border-cyber-border/70 pb-3">
              <Server className="w-4 h-4 text-cyber-permitted" />
              <h2 className="text-xs font-mono font-bold uppercase tracking-wider text-cyber-textPrimary">
                Integration Health
              </h2>
            </div>

            <div className="space-y-3">
              {integrations.map((integ) => (
                <div
                  key={integ.service_name}
                  className="p-3 bg-cyber-bg/60 border border-cyber-border rounded-lg space-y-1.5"
                >
                  <div className="flex items-center justify-between text-xs font-mono">
                    <span className="font-semibold text-cyber-textPrimary">{integ.display_name}</span>
                    <span className="text-[10px] text-cyber-permitted flex items-center gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-cyber-permitted inline-block" />
                      ONLINE
                    </span>
                  </div>
                  <p className="text-[11px] text-cyber-textMuted">{integ.status_message}</p>
                </div>
              ))}
            </div>

            <div className="pt-2">
              <div className="p-3 bg-cyber-accent/5 border border-cyber-accent/20 rounded-lg flex items-start gap-2.5">
                <Lock className="w-4 h-4 text-cyber-accent shrink-0 mt-0.5" />
                <div className="text-[11px] leading-relaxed text-cyber-textSecondary">
                  <strong className="text-cyber-textPrimary">Least-Privilege Enforcement:</strong> Integrations are
                  gated by dynamic, short-lived capabilities. No component retains permanent ambient privileges.
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </>
  );
}
