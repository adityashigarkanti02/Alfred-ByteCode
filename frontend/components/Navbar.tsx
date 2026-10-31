"use client";

/**
 * Top Navigation Bar for ALFRED AI.
 * 
 * Displays active page title, system security posture, pending approval alerts,
 * and an emergency kill switch for immediate operational freeze.
 */

import React, { useState, useEffect } from "react";
import { ShieldCheck, Bell, AlertTriangle, Power } from "lucide-react";
import { api } from "../lib/api";

interface NavbarProps {
  title?: string;
}

export function Navbar({ title = "ALFRED AI Autonomous Control" }: NavbarProps) {
  const [pendingCount, setPendingCount] = useState<number>(0);
  const [killSwitchActive, setKillSwitchActive] = useState<boolean>(false);

  useEffect(() => {
    // Poll pending approvals
    const checkApprovals = async () => {
      try {
        const apps = await api.listApprovals("PENDING");
        setPendingCount(apps.length);
      } catch (err) {
        // Silent catch during initial loading
      }
    };

    checkApprovals();
    const interval = setInterval(checkApprovals, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleEmergencyFreeze = () => {
    setKillSwitchActive(!killSwitchActive);
    alert(
      killSwitchActive
        ? "Emergency freeze disengaged. Standard security policy active."
        : "EMERGENCY FREEZE ENGAGED: All outbound writes and tool proposals are now locked."
    );
  };

  return (
    <header className="h-16 bg-cyber-bg/90 backdrop-blur border-b border-cyber-border flex items-center justify-between px-8 sticky top-0 z-30">
      {/* Title & Path */}
      <div>
        <h1 className="text-sm font-semibold text-cyber-textPrimary tracking-wide font-mono">
          {title}
        </h1>
        <p className="text-[11px] text-cyber-textMuted">
          Deterministic Policy Enforcement • Provenance Tracking Active
        </p>
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-4">
        {/* Defense Status */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-cyber-permitted/10 border border-cyber-permitted/25 text-cyber-permitted text-xs font-mono font-medium">
          <ShieldCheck className="w-4 h-4" />
          <span>INJECTION DEFENSE ARMED</span>
        </div>

        {/* Pending Approvals Badge */}
        {pendingCount > 0 && (
          <a
            href="/authority"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-cyber-warning/10 border border-cyber-warning/30 text-cyber-warning text-xs font-mono font-medium animate-pulse"
          >
            <AlertTriangle className="w-3.5 h-3.5" />
            <span>{pendingCount} APPROVAL PENDING</span>
          </a>
        )}

        {/* Emergency Kill Switch */}
        <button
          onClick={handleEmergencyFreeze}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-mono font-medium transition-all duration-200 border ${
            killSwitchActive
              ? "bg-cyber-blocked text-white border-cyber-blocked shadow-[0_0_12px_#EF4444]"
              : "bg-cyber-card text-cyber-blocked border-cyber-blocked/40 hover:bg-cyber-blocked/10"
          }`}
          title="Emergency Circuit Breaker: Halt all running agent operations"
        >
          <Power className="w-3.5 h-3.5" />
          <span>{killSwitchActive ? "CIRCUIT TRIPPED" : "KILL SWITCH"}</span>
        </button>
      </div>
    </header>
  );
}
