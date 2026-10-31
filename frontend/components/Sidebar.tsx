"use client";

/**
 * Cybersecurity SaaS Navigation Sidebar for ALFRED AI.
 * 
 * Provides links to all 8 core views:
 * Dashboard, Workspace, Emails, Browser, Local Files, Security Center, Authority, and Settings.
 * Displays live security posture badge and dynamic authority mode.
 */

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  ShieldAlert,
  LayoutDashboard,
  Terminal,
  Mail,
  Globe,
  FolderLock,
  ShieldCheck,
  KeyRound,
  Settings,
  Lock,
  Cpu,
} from "lucide-react";

const NAV_ITEMS = [
  { name: "Dashboard", href: "/", icon: LayoutDashboard },
  { name: "Agent Workspace", href: "/workspace", icon: Terminal },
  { name: "Email Management", href: "/emails", icon: Mail },
  { name: "Web Browser", href: "/browser", icon: Globe },
  { name: "Local File Manager", href: "/files", icon: FolderLock },
  { name: "Security Center", href: "/security", icon: ShieldCheck },
  { name: "Authority Center", href: "/authority", icon: KeyRound },
  { name: "Settings", href: "/settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 bg-cyber-sidebar border-r border-cyber-border flex flex-col h-screen select-none shrink-0">
      {/* Brand Header */}
      <div className="h-16 flex items-center px-6 border-b border-cyber-border gap-3">
        <div className="w-9 h-9 rounded-lg bg-cyber-accent/20 border border-cyber-accent/40 flex items-center justify-center text-cyber-accent shadow-sm">
          <ShieldAlert className="w-5 h-5" />
        </div>
        <div>
          <div className="text-sm font-bold tracking-wider text-cyber-textPrimary flex items-center gap-1.5 font-mono">
            ALFRED <span className="text-cyber-accent">AI</span>
          </div>
          <div className="text-[10px] text-cyber-textMuted tracking-tight font-mono">
            INJECTION-RESISTANT AGENT
          </div>
        </div>
      </div>

      {/* Navigation Menu */}
      <nav className="flex-1 py-4 px-3 space-y-1 overflow-y-auto">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-xs font-medium transition-all duration-150 ${
                isActive
                  ? "bg-cyber-card text-cyber-accent border border-cyber-accent/30 shadow-sm"
                  : "text-cyber-textSecondary hover:bg-cyber-card/60 hover:text-cyber-textPrimary"
              }`}
            >
              <Icon className={`w-4 h-4 ${isActive ? "text-cyber-accent" : "text-cyber-textMuted"}`} />
              <span>{item.name}</span>
              {isActive && (
                <div className="ml-auto w-1.5 h-1.5 rounded-full bg-cyber-accent shadow-[0_0_8px_#3B82F6]" />
              )}
            </Link>
          );
        })}
      </nav>

      {/* Security Status Card */}
      <div className="p-3 m-3 bg-cyber-card/70 border border-cyber-border rounded-lg space-y-2">
        <div className="flex items-center justify-between text-[11px] text-cyber-textSecondary">
          <span className="flex items-center gap-1.5">
            <Lock className="w-3.5 h-3.5 text-cyber-permitted" />
            Authority Engine
          </span>
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-cyber-permitted/10 text-cyber-permitted font-mono border border-cyber-permitted/20">
            L0 - L3
          </span>
        </div>
        <div className="flex items-center justify-between text-[11px] text-cyber-textSecondary">
          <span className="flex items-center gap-1.5">
            <Cpu className="w-3.5 h-3.5 text-cyber-accent" />
            Circuit Breaker
          </span>
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-cyber-accent/10 text-cyber-accent font-mono border border-cyber-accent/20">
            ARMED
          </span>
        </div>
      </div>
    </aside>
  );
}
