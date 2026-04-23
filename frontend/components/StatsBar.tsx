"use client";

import { ScrapeStatus } from "@/lib/types";
import { useEffect, useState } from "react";

interface StatsBarProps {
  leadCount: number;
  status: ScrapeStatus;
  startTime: number | null;
  sessionId: string | null;
}

export default function StatsBar({ leadCount, status, startTime, sessionId }: StatsBarProps) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (status !== "running" || !startTime) {
      return;
    }
    const interval = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startTime) / 1000));
    }, 1000);
    return () => clearInterval(interval);
  }, [status, startTime]);

  // Reset elapsed when not running
  useEffect(() => {
    if (status === "idle") setElapsed(0);
  }, [status]);

  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  const statusConfig: Record<ScrapeStatus, { color: string; label: string; pulse: boolean }> = {
    idle: { color: "bg-slate-500", label: "Idle", pulse: false },
    running: { color: "bg-emerald-500", label: "Scraping", pulse: true },
    complete: { color: "bg-cyan-500", label: "Complete", pulse: false },
    error: { color: "bg-red-500", label: "Error", pulse: false },
    stopped: { color: "bg-amber-500", label: "Stopped", pulse: false },
  };

  const { color, label, pulse } = statusConfig[status];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      {/* Status */}
      <div className="glass-card rounded-xl p-4 flex items-center gap-3">
        <div className="relative flex items-center justify-center">
          <div className={`w-3 h-3 rounded-full ${color}`} />
          {pulse && (
            <div className={`absolute w-3 h-3 rounded-full ${color} animate-ping`} />
          )}
        </div>
        <div>
          <p className="text-[10px] font-medium text-[var(--text-secondary)] uppercase tracking-widest">Status</p>
          <p className="text-sm font-semibold text-[var(--text-primary)]">{label}</p>
        </div>
      </div>

      {/* Lead Count */}
      <div className="glass-card rounded-xl p-4">
        <p className="text-[10px] font-medium text-[var(--text-secondary)] uppercase tracking-widest">Leads Found</p>
        <p className="text-2xl font-bold bg-gradient-to-r from-cyan-400 to-teal-400 bg-clip-text text-transparent">
          {leadCount}
        </p>
      </div>

      {/* Elapsed Time */}
      <div className="glass-card rounded-xl p-4">
        <p className="text-[10px] font-medium text-[var(--text-secondary)] uppercase tracking-widest">Elapsed</p>
        <p className="text-2xl font-bold text-[var(--text-primary)] font-mono">
          {formatTime(elapsed)}
        </p>
      </div>

      {/* Session */}
      <div className="glass-card rounded-xl p-4">
        <p className="text-[10px] font-medium text-[var(--text-secondary)] uppercase tracking-widest">Session</p>
        <p className="text-sm font-medium text-[var(--text-secondary)] truncate">
          {sessionId || "—"}
        </p>
      </div>
    </div>
  );
}
