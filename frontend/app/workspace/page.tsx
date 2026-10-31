"use client";

/**
 * Agent Workspace for ALFRED AI.
 * 
 * Provides an autonomous command console with:
 * - Natural-language task input
 * - Live execution timeline displaying planned steps, tool calls, and security decisions
 * - Real-time approval prompts for L2 actions
 * - Task cancellation controls
 * - Final task report visualization
 */

import React, { useState, useEffect } from "react";
import { Navbar } from "@/components/Navbar";
import {
  Send,
  Terminal,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  CheckCircle,
  XCircle,
  FileText,
  Clock,
  Ban,
  ArrowRight,
  Cpu,
} from "lucide-react";
import { api } from "@/lib/api";
import { TaskDetail, TaskItem } from "@/lib/types";

export default function WorkspacePage() {
  const [prompt, setPrompt] = useState<string>("");
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);
  const [taskDetail, setTaskDetail] = useState<TaskDetail | null>(null);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Poll active task details
  useEffect(() => {
    if (!activeTaskId) return;

    const pollTask = async () => {
      try {
        const details = await api.getTaskDetails(activeTaskId);
        setTaskDetail(details);
      } catch (err: any) {
        console.error("Error polling task:", err);
      }
    };

    pollTask();
    const interval = setInterval(pollTask, 2000);
    return () => clearInterval(interval);
  }, [activeTaskId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim() || submitting) return;

    setSubmitting(true);
    setErrorMsg(null);
    try {
      const res = await api.createTask(prompt);
      setActiveTaskId(res.task_id);
      setPrompt("");
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to submit task");
    } finally {
      setSubmitting(false);
    }
  };

  const handleApproval = async (approved: boolean) => {
    if (!activeTaskId) return;
    try {
      await api.decideApproval(activeTaskId, approved);
      // Immediately refresh task details
      const updated = await api.getTaskDetails(activeTaskId);
      setTaskDetail(updated);
    } catch (err: any) {
      alert(`Approval error: ${err.message}`);
    }
  };

  const handleCancel = async () => {
    if (!activeTaskId) return;
    try {
      await api.cancelTask(activeTaskId);
      const updated = await api.getTaskDetails(activeTaskId);
      setTaskDetail(updated);
    } catch (err: any) {
      alert(`Cancellation error: ${err.message}`);
    }
  };

  return (
    <>
      <Navbar title="Agent Workspace & Execution Console" />
      <main className="p-8 space-y-6 flex-1 flex flex-col min-h-0">
        {/* Natural Language Task Input Box */}
        <div className="bg-cyber-card border border-cyber-border rounded-xl p-5 shadow-sm">
          <form onSubmit={handleSubmit} className="space-y-3">
            <div className="flex items-center justify-between">
              <label className="text-xs font-mono font-bold uppercase tracking-wider text-cyber-textSecondary flex items-center gap-2">
                <Terminal className="w-4 h-4 text-cyber-accent" />
                Issue Natural-Language Instruction
              </label>
              <span className="text-[11px] text-cyber-textMuted font-mono">
                Decoupled Planner • Independent Security Gateway
              </span>
            </div>

            <div className="flex gap-3">
              <input
                type="text"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="e.g. Read my latest emails and summarize important messages..."
                disabled={submitting}
                className="flex-1 bg-cyber-bg border border-cyber-border rounded-lg px-4 py-3 text-sm text-cyber-textPrimary focus:outline-none focus:border-cyber-accent font-sans transition-colors placeholder:text-cyber-textMuted"
              />
              <button
                type="submit"
                disabled={submitting || !prompt.trim()}
                className="bg-cyber-accent hover:bg-cyber-accent/90 disabled:opacity-50 text-white px-5 py-3 rounded-lg font-mono text-xs font-semibold flex items-center gap-2 transition-all shadow-sm"
              >
                <Send className="w-3.5 h-3.5" />
                <span>{submitting ? "PLANNING..." : "EXECUTE"}</span>
              </button>
            </div>

            {errorMsg && (
              <div className="text-xs text-cyber-blocked font-mono flex items-center gap-1.5 pt-1">
                <AlertTriangle className="w-3.5 h-3.5" />
                <span>{errorMsg}</span>
              </div>
            )}
          </form>
        </div>

        {/* Live Execution Timeline & Task View */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 flex-1 min-h-0">
          {/* Main Execution Log (2 Cols) */}
          <div className="lg:col-span-2 bg-cyber-card border border-cyber-border rounded-xl p-6 flex flex-col min-h-0 shadow-sm">
            <div className="flex items-center justify-between border-b border-cyber-border/70 pb-3 mb-4">
              <div className="flex items-center gap-2 font-mono text-xs font-bold uppercase text-cyber-textPrimary">
                <Cpu className="w-4 h-4 text-cyber-accent" />
                <span>Execution Timeline & Tool Telemetry</span>
              </div>
              {taskDetail && (
                <div className="flex items-center gap-2">
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold uppercase tracking-wider border ${
                      taskDetail.status === "COMPLETED"
                        ? "bg-cyber-permitted/10 text-cyber-permitted border-cyber-permitted/30"
                        : taskDetail.status === "AWAITING_APPROVAL"
                        ? "bg-cyber-warning/10 text-cyber-warning border-cyber-warning/30"
                        : taskDetail.status === "BLOCKED_ATTACK"
                        ? "bg-cyber-blocked/10 text-cyber-blocked border-cyber-blocked/30"
                        : "bg-cyber-accent/10 text-cyber-accent border-cyber-accent/30"
                    }`}
                  >
                    {taskDetail.status}
                  </span>
                  {["PLANNING", "EXECUTING", "AWAITING_APPROVAL"].includes(taskDetail.status) && (
                    <button
                      onClick={handleCancel}
                      className="px-2 py-0.5 rounded text-[10px] font-mono text-cyber-blocked hover:bg-cyber-blocked/10 border border-cyber-blocked/30 flex items-center gap-1"
                    >
                      <Ban className="w-3 h-3" />
                      CANCEL
                    </button>
                  )}
                </div>
              )}
            </div>

            {/* Task Prompt Display */}
            {taskDetail && (
              <div className="mb-4 p-3 bg-cyber-bg/70 border border-cyber-border rounded-lg text-xs font-mono text-cyber-textSecondary">
                <span className="text-cyber-accent font-semibold">Active Instruction:</span> {taskDetail.prompt}
              </div>
            )}

            {/* Pending Approval Callout Banner if AWAITING_APPROVAL */}
            {taskDetail?.status === "AWAITING_APPROVAL" && (
              <div className="mb-4 p-4 bg-cyber-warning/10 border border-cyber-warning/30 rounded-xl space-y-3">
                <div className="flex items-center gap-2 text-cyber-warning font-mono text-xs font-bold uppercase">
                  <AlertTriangle className="w-4 h-4" />
                  <span>L2 Human Authorization Required</span>
                </div>
                <p className="text-xs text-cyber-textPrimary">
                  The agent proposed a sensitive external action. Review the immutable parameters below before granting capability.
                </p>
                <div className="flex items-center gap-3 pt-1">
                  <button
                    onClick={() => handleApproval(true)}
                    className="px-4 py-2 rounded-lg bg-cyber-permitted hover:bg-cyber-permitted/90 text-white font-mono text-xs font-semibold flex items-center gap-1.5 shadow-sm"
                  >
                    <CheckCircle className="w-3.5 h-3.5" />
                    AUTHORIZE & PROCEED
                  </button>
                  <button
                    onClick={() => handleApproval(false)}
                    className="px-4 py-2 rounded-lg bg-cyber-blocked/20 hover:bg-cyber-blocked/30 border border-cyber-blocked/40 text-cyber-blocked font-mono text-xs font-semibold flex items-center gap-1.5"
                  >
                    <XCircle className="w-3.5 h-3.5" />
                    DENY ACTION
                  </button>
                </div>
              </div>
            )}

            {/* Steps & Tool Calls Timeline */}
            <div className="flex-1 overflow-y-auto space-y-3 pr-2">
              {taskDetail && taskDetail.tool_calls.length > 0 ? (
                taskDetail.tool_calls.map((tc, idx) => (
                  <div
                    key={tc.id || idx}
                    className="p-3.5 bg-cyber-bg/80 border border-cyber-border rounded-lg text-xs space-y-2"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 font-mono">
                        <span className="text-cyber-textMuted font-bold">#{idx + 1}</span>
                        <span className="text-cyber-accent font-semibold">{tc.tool_name}</span>
                        <span className="text-cyber-textMuted">•</span>
                        <span className="text-cyber-textPrimary">{tc.operation}</span>
                      </div>
                      <span
                        className={`px-1.5 py-0.5 rounded text-[10px] font-mono border ${
                          tc.status === "EXECUTED"
                            ? "bg-cyber-permitted/10 text-cyber-permitted border-cyber-permitted/20"
                            : tc.status === "FAILED"
                            ? "bg-cyber-blocked/10 text-cyber-blocked border-cyber-blocked/20"
                            : "bg-cyber-warning/10 text-cyber-warning border-cyber-warning/20"
                        }`}
                      >
                        {tc.status}
                      </span>
                    </div>

                    {/* Parameters Snapshot */}
                    <div className="p-2 bg-cyber-card/90 rounded border border-cyber-border/40 font-mono text-[11px] text-cyber-textSecondary overflow-x-auto">
                      <span className="text-cyber-textMuted">Params: </span>
                      {JSON.stringify(tc.arguments)}
                    </div>

                    {/* Result or Error */}
                    {tc.execution_result && (
                      <div className="text-[11px] text-cyber-textSecondary font-mono truncate">
                        <span className="text-cyber-permitted">Output: </span>
                        {typeof tc.execution_result === "object"
                          ? JSON.stringify(tc.execution_result)
                          : String(tc.execution_result)}
                      </div>
                    )}
                    {tc.error_message && (
                      <div className="text-[11px] text-cyber-blocked font-mono">
                        Error: {tc.error_message}
                      </div>
                    )}
                  </div>
                ))
              ) : (
                <div className="h-48 flex flex-col items-center justify-center text-cyber-textMuted text-xs font-mono">
                  <Terminal className="w-8 h-8 text-cyber-textMuted/40 mb-2" />
                  <span>No active execution. Issue an instruction above.</span>
                </div>
              )}
            </div>
          </div>

          {/* Right Column: Final Report & Security Findings */}
          <div className="bg-cyber-card border border-cyber-border rounded-xl p-6 flex flex-col min-h-0 shadow-sm space-y-4">
            <div className="flex items-center gap-2 border-b border-cyber-border/70 pb-3 font-mono text-xs font-bold uppercase text-cyber-textPrimary">
              <FileText className="w-4 h-4 text-cyber-accent" />
              <span>Final Task Report</span>
            </div>

            <div className="flex-1 overflow-y-auto bg-cyber-bg/70 border border-cyber-border rounded-lg p-4 font-mono text-xs text-cyber-textSecondary leading-relaxed whitespace-pre-wrap">
              {taskDetail?.final_report ? (
                taskDetail.final_report
              ) : (
                <span className="text-cyber-textMuted">
                  The task report will be generated and verified here upon completion or resolution.
                </span>
              )}
            </div>

            <div className="p-3 bg-cyber-bg/60 border border-cyber-border rounded-lg text-[11px] text-cyber-textMuted font-mono space-y-1">
              <div className="text-cyber-textSecondary font-semibold">Security Verification Notice:</div>
              <div>
                Outputs from external sources remain tagged with <code className="text-cyber-warning">UNTRUSTED_EXTERNAL</code> and cannot bypass authorization gates.
              </div>
            </div>
          </div>
        </div>
      </main>
    </>
  );
}
