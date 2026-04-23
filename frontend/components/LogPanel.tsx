"use client";

import { useEffect, useRef } from "react";

interface LogPanelProps {
  logs: string[];
  isVisible: boolean;
  onToggle: () => void;
}

export default function LogPanel({ logs, isVisible, onToggle }: LogPanelProps) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  return (
    <div className="glass-card rounded-2xl overflow-hidden">
      <button onClick={onToggle}
        className="w-full flex items-center gap-3 px-6 py-3 border-b border-[var(--border-subtle)] hover:bg-[var(--border-subtle)] transition-colors">
        <svg className={`w-4 h-4 text-[var(--text-secondary)] transition-transform ${isVisible ? "rotate-90" : ""}`}
          fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
        </svg>
        <span className="text-sm font-medium text-[var(--text-secondary)]">Scraper Logs</span>
        <span className="ml-auto text-xs text-[var(--text-secondary)]">{logs.length} entries</span>
      </button>
      {isVisible && (
        <div className="max-h-48 overflow-y-auto p-4 font-mono text-xs text-[var(--text-secondary)] space-y-0.5 scrollbar-thin">
          {logs.length === 0 && <p className="text-[var(--text-secondary)]">No logs yet…</p>}
          {logs.map((log, i) => (
            <p key={i} className="leading-relaxed break-all">{log}</p>
          ))}
          <div ref={endRef} />
        </div>
      )}
    </div>
  );
}
