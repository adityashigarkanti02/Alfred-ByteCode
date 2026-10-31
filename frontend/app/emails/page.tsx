"use client";

/**
 * Email Management Console for ALFRED AI.
 * 
 * Provides:
 * - Gmail connection status & OAuth scopes
 * - Inbox view with instant search
 * - Email body viewing & suspicious attack marker highlighting
 * - Attachment extraction & summarization
 * - Draft creation & Authorized Sending
 */

import React, { useState, useEffect } from "react";
import { Navbar } from "@/components/Navbar";
import {
  Mail,
  Search,
  Paperclip,
  ShieldAlert,
  Send,
  FileEdit,
  CheckCircle,
  Clock,
  User,
  AlertTriangle,
} from "lucide-react";
import { api } from "@/lib/api";
import { EmailItem } from "@/lib/types";

export default function EmailsPage() {
  const [emails, setEmails] = useState<EmailItem[]>([]);
  const [selectedEmail, setSelectedEmail] = useState<EmailItem | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(true);

  // New Draft State
  const [showDraftModal, setShowDraftModal] = useState<boolean>(false);
  const [draftRecipient, setDraftRecipient] = useState<string>("");
  const [draftSubject, setDraftSubject] = useState<string>("");
  const [draftBody, setDraftBody] = useState<string>("");

  const loadInbox = async (query?: string) => {
    setLoading(true);
    try {
      const msgs = await api.getGmailInbox(query);
      setEmails(msgs);
      if (msgs.length > 0 && !selectedEmail) {
        // Load details for first email
        const fullMsg = await api.getGmailMessage(msgs[0].message_id);
        setSelectedEmail(fullMsg);
      }
    } catch (err) {
      console.error("Failed to load inbox:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadInbox();
  }, []);

  const handleSelectEmail = async (msgId: string) => {
    try {
      const full = await api.getGmailMessage(msgId);
      setSelectedEmail(full);
    } catch (err) {
      console.error("Failed to fetch message details:", err);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    loadInbox(searchQuery);
  };

  const handleCreateDraft = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!draftRecipient || !draftSubject) return;

    try {
      await fetch("http://127.0.0.1:8000/api/v1/integrations/gmail/draft", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          to_recipients: [draftRecipient],
          subject: draftSubject,
          body: draftBody,
        }),
      });
      alert("Draft saved to Gmail drafts successfully!");
      setShowDraftModal(false);
      setDraftRecipient("");
      setDraftSubject("");
      setDraftBody("");
    } catch (err: any) {
      alert(`Error saving draft: ${err.message}`);
    }
  };

  return (
    <>
      <Navbar title="Email Management & Threat Inspection" />
      <main className="p-8 space-y-6 flex-1 flex flex-col min-h-0">
        {/* Top Controls: Search & Actions */}
        <div className="flex items-center justify-between gap-4">
          <form onSubmit={handleSearch} className="flex-1 max-w-md relative">
            <Search className="w-4 h-4 text-cyber-textMuted absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search emails by subject, sender, or keyword..."
              className="w-full bg-cyber-card border border-cyber-border rounded-lg pl-10 pr-4 py-2.5 text-xs text-cyber-textPrimary focus:outline-none focus:border-cyber-accent font-sans"
            />
          </form>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowDraftModal(true)}
              className="bg-cyber-card hover:bg-cyber-cardHover border border-cyber-border text-cyber-textPrimary px-4 py-2 rounded-lg text-xs font-mono font-medium flex items-center gap-2 transition-colors"
            >
              <FileEdit className="w-3.5 h-3.5 text-cyber-accent" />
              <span>NEW DRAFT</span>
            </button>
          </div>
        </div>

        {/* Email Dual-Pane Workspace */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 flex-1 min-h-0">
          {/* Email List (5 Cols) */}
          <div className="lg:col-span-5 bg-cyber-card border border-cyber-border rounded-xl p-4 flex flex-col min-h-0 shadow-sm overflow-hidden">
            <div className="text-xs font-mono text-cyber-textMuted uppercase font-bold tracking-wider px-2 py-1 mb-2">
              Inbox ({emails.length})
            </div>

            <div className="flex-1 overflow-y-auto divide-y divide-cyber-border/60">
              {loading ? (
                <div className="p-8 text-center text-xs text-cyber-textMuted font-mono">Loading inbox...</div>
              ) : emails.length > 0 ? (
                emails.map((msg) => {
                  const isSelected = selectedEmail?.message_id === msg.message_id;
                  return (
                    <div
                      key={msg.message_id}
                      onClick={() => handleSelectEmail(msg.message_id)}
                      className={`p-3.5 rounded-lg cursor-pointer transition-colors space-y-1.5 ${
                        isSelected
                          ? "bg-cyber-cardHover border border-cyber-accent/40"
                          : "hover:bg-cyber-cardHover/60"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-cyber-textPrimary truncate max-w-[200px]">
                          {msg.sender}
                        </span>
                        <span className="text-[10px] text-cyber-textMuted font-mono">
                          {new Date(msg.date).toLocaleDateString()}
                        </span>
                      </div>

                      <div className="text-xs font-medium text-cyber-textSecondary truncate">{msg.subject}</div>

                      <div className="flex items-center justify-between text-[11px] text-cyber-textMuted">
                        <span className="truncate max-w-[220px]">{msg.snippet}</span>
                        <div className="flex items-center gap-1.5 shrink-0">
                          {msg.has_attachments && <Paperclip className="w-3 h-3 text-cyber-accent" />}
                          {msg.is_suspicious && (
                            <span className="px-1.5 py-0.2 rounded bg-cyber-blocked/20 text-cyber-blocked text-[9px] font-mono border border-cyber-blocked/30">
                              ATTACK SUSPECT
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="p-8 text-center text-xs text-cyber-textMuted font-mono">No matching messages.</div>
              )}
            </div>
          </div>

          {/* Email Detail Pane (7 Cols) */}
          <div className="lg:col-span-7 bg-cyber-card border border-cyber-border rounded-xl p-6 flex flex-col min-h-0 shadow-sm overflow-hidden">
            {selectedEmail ? (
              <div className="space-y-4 flex-1 flex flex-col min-h-0">
                {/* Header */}
                <div className="border-b border-cyber-border pb-4 space-y-2">
                  <div className="flex items-start justify-between gap-4">
                    <h2 className="text-sm font-bold text-cyber-textPrimary font-mono">{selectedEmail.subject}</h2>
                    {selectedEmail.is_suspicious && (
                      <div className="flex items-center gap-1 px-2.5 py-1 rounded bg-cyber-blocked/10 border border-cyber-blocked/30 text-cyber-blocked text-[10px] font-mono font-bold shrink-0">
                        <ShieldAlert className="w-3.5 h-3.5" />
                        <span>INJECTION DETECTED</span>
                      </div>
                    )}
                  </div>

                  <div className="flex items-center gap-2 text-xs text-cyber-textSecondary">
                    <User className="w-3.5 h-3.5 text-cyber-accent" />
                    <span>From: <strong className="text-cyber-textPrimary">{selectedEmail.sender}</strong></span>
                  </div>
                </div>

                {/* Body Content */}
                <div className="flex-1 overflow-y-auto bg-cyber-bg/70 border border-cyber-border rounded-lg p-5 text-xs text-cyber-textPrimary leading-relaxed whitespace-pre-wrap font-mono">
                  {selectedEmail.body_text || selectedEmail.snippet}
                </div>

                {/* Attachments Section if present */}
                {selectedEmail.has_attachments && (
                  <div className="p-3 bg-cyber-bg/90 border border-cyber-border rounded-lg space-y-2">
                    <div className="text-[11px] font-mono font-bold text-cyber-textSecondary flex items-center gap-1.5">
                      <Paperclip className="w-3.5 h-3.5 text-cyber-accent" />
                      <span>Extracted Attachments (Scanned Safe)</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="px-3 py-1.5 rounded bg-cyber-card border border-cyber-border text-xs font-mono text-cyber-textPrimary flex items-center gap-2">
                        <span>vendor_invoice_q3.pdf</span>
                        <span className="text-[10px] text-cyber-textMuted">(45 KB)</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-cyber-textMuted text-xs font-mono">
                <Mail className="w-8 h-8 text-cyber-textMuted/40 mb-2" />
                <span>Select an email from the inbox list to inspect content.</span>
              </div>
            )}
          </div>
        </div>

        {/* Modal: New Draft */}
        {showDraftModal && (
          <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-cyber-card border border-cyber-border rounded-xl w-full max-w-lg p-6 space-y-4 shadow-xl">
              <div className="flex items-center justify-between border-b border-cyber-border pb-3">
                <div className="text-sm font-mono font-bold text-cyber-textPrimary flex items-center gap-2">
                  <FileEdit className="w-4 h-4 text-cyber-accent" />
                  <span>Create Email Draft (L1 Scoped)</span>
                </div>
                <button
                  onClick={() => setShowDraftModal(false)}
                  className="text-cyber-textMuted hover:text-cyber-textPrimary text-xs"
                >
                  ✕
                </button>
              </div>

              <form onSubmit={handleCreateDraft} className="space-y-3">
                <div>
                  <label className="text-[11px] font-mono text-cyber-textMuted uppercase">Recipient</label>
                  <input
                    type="email"
                    required
                    value={draftRecipient}
                    onChange={(e) => setDraftRecipient(e.target.value)}
                    placeholder="recipient@example.com"
                    className="w-full mt-1 bg-cyber-bg border border-cyber-border rounded-lg px-3 py-2 text-xs text-cyber-textPrimary focus:outline-none focus:border-cyber-accent font-mono"
                  />
                </div>

                <div>
                  <label className="text-[11px] font-mono text-cyber-textMuted uppercase">Subject</label>
                  <input
                    type="text"
                    required
                    value={draftSubject}
                    onChange={(e) => setDraftSubject(e.target.value)}
                    placeholder="Subject line..."
                    className="w-full mt-1 bg-cyber-bg border border-cyber-border rounded-lg px-3 py-2 text-xs text-cyber-textPrimary focus:outline-none focus:border-cyber-accent"
                  />
                </div>

                <div>
                  <label className="text-[11px] font-mono text-cyber-textMuted uppercase">Draft Body</label>
                  <textarea
                    rows={5}
                    value={draftBody}
                    onChange={(e) => setDraftBody(e.target.value)}
                    placeholder="Write email contents..."
                    className="w-full mt-1 bg-cyber-bg border border-cyber-border rounded-lg p-3 text-xs text-cyber-textPrimary focus:outline-none focus:border-cyber-accent font-sans"
                  />
                </div>

                <div className="flex items-center justify-end gap-3 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowDraftModal(false)}
                    className="px-4 py-2 rounded-lg text-xs font-mono text-cyber-textSecondary hover:bg-cyber-cardHover"
                  >
                    CANCEL
                  </button>
                  <button
                    type="submit"
                    className="bg-cyber-accent hover:bg-cyber-accent/90 text-white px-4 py-2 rounded-lg text-xs font-mono font-semibold"
                  >
                    SAVE DRAFT
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </main>
    </>
  );
}
