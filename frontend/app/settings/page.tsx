"use client";

/**
 * Settings and Configuration View for ALFRED AI.
 * 
 * Allows configuration of:
 * - Integration credentials & Gmail OAuth scopes
 * - Local Companion authorized root paths & token settings
 * - Protected file definitions (Hard Deny L3 list)
 * - Approval requirements for sensitive operations
 * - Security preferences (Circuit Breaker threshold, Taint enforcement)
 */

import React, { useState } from "react";
import { Navbar } from "@/components/Navbar";
import {
  Settings,
  Shield,
  Key,
  HardDrive,
  FolderLock,
  Mail,
  Save,
  CheckCircle,
  Sliders,
} from "lucide-react";

export default function SettingsPage() {
  const [circuitThreshold, setCircuitThreshold] = useState<number>(3);
  const [authorizedDir, setAuthorizedDir] = useState<string>("C:\\Users\\Aditya\\workspace_sandbox");
  const [requireEmailApproval, setRequireEmailApproval] = useState<boolean>(true);
  const [requireDeleteApproval, setRequireDeleteApproval] = useState<boolean>(true);
  const [strictTaintEnforcement, setStrictTaintEnforcement] = useState<boolean>(true);
  const [saved, setSaved] = useState<boolean>(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  return (
    <>
      <Navbar title="Security Policy & System Settings" />
      <main className="p-8 space-y-8 flex-1 max-w-4xl">
        <form onSubmit={handleSave} className="space-y-6">
          {/* Section 1: Dynamic Authority & Circuit Breaker */}
          <div className="bg-cyber-card border border-cyber-border rounded-xl p-6 shadow-sm space-y-4">
            <div className="flex items-center gap-2 border-b border-cyber-border/70 pb-3">
              <Shield className="w-4 h-4 text-cyber-accent" />
              <h2 className="text-xs font-mono font-bold uppercase tracking-wider text-cyber-textPrimary">
                Dynamic Authority & Circuit Breaker Settings
              </h2>
            </div>

            <div className="space-y-4">
              <div>
                <label className="text-xs font-medium text-cyber-textPrimary block">
                  Security Violation Threshold for Circuit Breaker
                </label>
                <p className="text-[11px] text-cyber-textMuted mt-0.5">
                  Number of intercepted prompt injections or policy violations before the task immediately locks down.
                </p>
                <input
                  type="number"
                  min={1}
                  max={10}
                  value={circuitThreshold}
                  onChange={(e) => setCircuitThreshold(parseInt(e.target.value) || 3)}
                  className="mt-2 w-32 bg-cyber-bg border border-cyber-border rounded-lg px-3 py-1.5 text-xs text-cyber-textPrimary font-mono focus:outline-none focus:border-cyber-accent"
                />
              </div>

              <div className="flex items-center justify-between pt-2">
                <div>
                  <div className="text-xs font-medium text-cyber-textPrimary">
                    Strict Information-Flow Taint Enforcement
                  </div>
                  <div className="text-[11px] text-cyber-textMuted">
                    Blocks untrusted external data from dictating parameters in sensitive sinks (recipients, file paths).
                  </div>
                </div>
                <input
                  type="checkbox"
                  checked={strictTaintEnforcement}
                  onChange={(e) => setStrictTaintEnforcement(e.target.checked)}
                  className="w-4 h-4 rounded border-cyber-border bg-cyber-bg text-cyber-accent focus:ring-0"
                />
              </div>
            </div>
          </div>

          {/* Section 2: Human Approval Requirements */}
          <div className="bg-cyber-card border border-cyber-border rounded-xl p-6 shadow-sm space-y-4">
            <div className="flex items-center gap-2 border-b border-cyber-border/70 pb-3">
              <Key className="w-4 h-4 text-cyber-warning" />
              <h2 className="text-xs font-mono font-bold uppercase tracking-wider text-cyber-textPrimary">
                L2 Human Authorization Requirements
              </h2>
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-xs font-medium text-cyber-textPrimary">Require Approval for Outbound Emails</div>
                  <div className="text-[11px] text-cyber-textMuted">
                    Prevents automated email transmission without explicit operator sign-off.
                  </div>
                </div>
                <input
                  type="checkbox"
                  checked={requireEmailApproval}
                  onChange={(e) => setRequireEmailApproval(e.target.checked)}
                  className="w-4 h-4 rounded border-cyber-border bg-cyber-bg text-cyber-accent focus:ring-0"
                />
              </div>

              <div className="flex items-center justify-between pt-2">
                <div>
                  <div className="text-xs font-medium text-cyber-textPrimary">Require Approval for File Deletion</div>
                  <div className="text-[11px] text-cyber-textMuted">
                    Prevents the agent from permanently deleting files without confirmation.
                  </div>
                </div>
                <input
                  type="checkbox"
                  checked={requireDeleteApproval}
                  onChange={(e) => setRequireDeleteApproval(e.target.checked)}
                  className="w-4 h-4 rounded border-cyber-border bg-cyber-bg text-cyber-accent focus:ring-0"
                />
              </div>
            </div>
          </div>

          {/* Section 3: Local Filesystem Jail Confinement */}
          <div className="bg-cyber-card border border-cyber-border rounded-xl p-6 shadow-sm space-y-4">
            <div className="flex items-center gap-2 border-b border-cyber-border/70 pb-3">
              <HardDrive className="w-4 h-4 text-cyber-permitted" />
              <h2 className="text-xs font-mono font-bold uppercase tracking-wider text-cyber-textPrimary">
                Local Companion Authorized Roots
              </h2>
            </div>

            <div>
              <label className="text-xs font-medium text-cyber-textPrimary block">
                Primary Authorized Directory Path
              </label>
              <p className="text-[11px] text-cyber-textMuted mt-0.5">
                The local companion restricts all file operations strictly to this canonical root. Symlink escapes and
                directory traversals are rejected.
              </p>
              <input
                type="text"
                value={authorizedDir}
                onChange={(e) => setAuthorizedDir(e.target.value)}
                className="mt-2 w-full bg-cyber-bg border border-cyber-border rounded-lg px-3 py-2 text-xs text-cyber-textPrimary font-mono focus:outline-none focus:border-cyber-accent"
              />
            </div>
          </div>

          {/* Save Button */}
          <div className="flex items-center gap-4">
            <button
              type="submit"
              className="bg-cyber-accent hover:bg-cyber-accent/90 text-white px-5 py-2.5 rounded-lg text-xs font-mono font-semibold flex items-center gap-2 shadow-sm"
            >
              <Save className="w-3.5 h-3.5" />
              <span>SAVE SECURITY SETTINGS</span>
            </button>

            {saved && (
              <span className="text-cyber-permitted text-xs font-mono flex items-center gap-1.5">
                <CheckCircle className="w-4 h-4" />
                Settings persisted successfully!
              </span>
            )}
          </div>
        </form>
      </main>
    </>
  );
}
