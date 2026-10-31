import React from "react";
import "./globals.css";
import { Sidebar } from "@/components/Sidebar";

export const metadata = {
  title: "ALFRED AI — Prompt-Injection-Resistant Autonomous Agent",
  description: "Next-generation autonomous agent protected by Dynamic Authority and Cryptographic Capabilities.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-cyber-bg text-cyber-textPrimary min-h-screen flex antialiased">
        <Sidebar />
        <div className="flex-1 flex flex-col min-w-0 overflow-y-auto">
          {children}
        </div>
      </body>
    </html>
  );
}
