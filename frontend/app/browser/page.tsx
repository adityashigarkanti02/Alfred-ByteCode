"use client";

/**
 * Secure Web Browser Interface for ALFRED AI.
 * 
 * Features:
 * - Direct URL navigation & live content extraction
 * - SSRF guard status indicator
 * - Inspection of hidden HTML comments & zero-sized DOM elements
 * - Extracted links viewer
 */

import React, { useState } from "react";
import { Navbar } from "@/components/Navbar";
import {
  Globe,
  Search,
  ShieldCheck,
  ShieldAlert,
  ArrowRight,
  ExternalLink,
  Code,
  FileCode,
  Lock,
} from "lucide-react";
import { api } from "@/lib/api";

export default function BrowserPage() {
  const [url, setUrl] = useState<string>("https://news.ycombinator.com");
  const [loading, setLoading] = useState<boolean>(false);
  const [extraction, setExtraction] = useState<any>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleNavigate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim() || loading) return;

    setLoading(true);
    setErrorMsg(null);
    try {
      const res = await api.browseUrl(url);
      setExtraction(res);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to browse webpage");
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Navbar title="Secure Isolated Web Browser" />
      <main className="p-8 space-y-6 flex-1 flex flex-col min-h-0">
        {/* Navigation Bar */}
        <div className="bg-cyber-card border border-cyber-border rounded-xl p-4 shadow-sm space-y-2">
          <form onSubmit={handleNavigate} className="flex gap-3">
            <div className="flex-1 relative">
              <Globe className="w-4 h-4 text-cyber-textMuted absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="url"
                required
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://example.com"
                className="w-full bg-cyber-bg border border-cyber-border rounded-lg pl-10 pr-4 py-2.5 text-xs text-cyber-textPrimary focus:outline-none focus:border-cyber-accent font-mono"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="bg-cyber-accent hover:bg-cyber-accent/90 disabled:opacity-50 text-white px-5 py-2.5 rounded-lg font-mono text-xs font-semibold flex items-center gap-2"
            >
              <span>{loading ? "FETCHING..." : "NAVIGATE"}</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </form>

          <div className="flex items-center gap-4 text-[11px] text-cyber-textMuted font-mono px-1">
            <span className="flex items-center gap-1 text-cyber-permitted">
              <Lock className="w-3 h-3" /> SSRF Hardwall Active
            </span>
            <span>•</span>
            <span>JavaScript Execution: Sandboxed Static</span>
            <span>•</span>
            <span>Private Subnets Blocked (RFC 1918)</span>
          </div>

          {errorMsg && (
            <div className="text-xs text-cyber-blocked font-mono flex items-center gap-1.5 p-2 bg-cyber-blocked/10 border border-cyber-blocked/30 rounded">
              <ShieldAlert className="w-4 h-4 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}
        </div>

        {/* Browser Content & DOM Inspector */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 flex-1 min-h-0">
          {/* Main Extracted Text Content (8 Cols) */}
          <div className="lg:col-span-8 bg-cyber-card border border-cyber-border rounded-xl p-6 flex flex-col min-h-0 shadow-sm overflow-hidden">
            <div className="flex items-center justify-between border-b border-cyber-border/70 pb-3 mb-3 font-mono text-xs">
              <span className="font-bold uppercase text-cyber-textPrimary">Visible Rendered Text</span>
              {extraction && (
                <span className="text-[10px] text-cyber-textMuted">
                  Status: {extraction.status_code} • Title: {extraction.title || "Untitled"}
                </span>
              )}
            </div>

            <div className="flex-1 overflow-y-auto bg-cyber-bg/70 border border-cyber-border rounded-lg p-5 font-mono text-xs text-cyber-textPrimary leading-relaxed whitespace-pre-wrap">
              {extraction ? (
                extraction.text_content || "Page returned empty body text."
              ) : (
                <span className="text-cyber-textMuted">
                  Enter an external URL above and click Navigate to extract web content safely.
                </span>
              )}
            </div>
          </div>

          {/* Hidden Comments & Links Inspector (4 Cols) */}
          <div className="lg:col-span-4 space-y-6 flex flex-col min-h-0">
            {/* Hidden Comments Card */}
            <div className="bg-cyber-card border border-cyber-border rounded-xl p-5 flex flex-col h-1/2 min-h-0 shadow-sm overflow-hidden">
              <div className="flex items-center gap-2 border-b border-cyber-border/70 pb-2.5 mb-2 font-mono text-xs font-bold text-cyber-warning uppercase">
                <Code className="w-3.5 h-3.5" />
                <span>Hidden HTML Comments ({extraction?.hidden_comments?.length || 0})</span>
              </div>

              <div className="flex-1 overflow-y-auto space-y-2">
                {extraction?.hidden_comments && extraction.hidden_comments.length > 0 ? (
                  extraction.hidden_comments.map((comment: string, i: number) => (
                    <div
                      key={i}
                      className="p-2 bg-cyber-bg border border-cyber-border rounded font-mono text-[10px] text-cyber-warning break-all"
                    >
                      &lt;!-- {comment} --&gt;
                    </div>
                  ))
                ) : (
                  <div className="text-[11px] text-cyber-textMuted font-mono text-center py-6">
                    No hidden comments found.
                  </div>
                )}
              </div>
            </div>

            {/* Extracted Links Card */}
            <div className="bg-cyber-card border border-cyber-border rounded-xl p-5 flex flex-col h-1/2 min-h-0 shadow-sm overflow-hidden">
              <div className="flex items-center gap-2 border-b border-cyber-border/70 pb-2.5 mb-2 font-mono text-xs font-bold text-cyber-accent uppercase">
                <ExternalLink className="w-3.5 h-3.5" />
                <span>Extracted Links ({extraction?.links?.length || 0})</span>
              </div>

              <div className="flex-1 overflow-y-auto space-y-1.5 divide-y divide-cyber-border/40">
                {extraction?.links && extraction.links.length > 0 ? (
                  extraction.links.map((link: any, i: number) => (
                    <div key={i} className="pt-1.5 first:pt-0 text-[11px] font-mono truncate">
                      <div className="text-cyber-textPrimary truncate">{link.text}</div>
                      <div className="text-cyber-textMuted text-[9px] truncate">{link.href}</div>
                    </div>
                  ))
                ) : (
                  <div className="text-[11px] text-cyber-textMuted font-mono text-center py-6">
                    No links extracted.
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </main>
    </>
  );
}
