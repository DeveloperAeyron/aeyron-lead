"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Lead } from "@/lib/types";
import LeadTable from "@/components/LeadTable";
import ExportBar from "@/components/ExportBar";

interface Session {
  session_id: string;
  has_xlsx: boolean;
  lead_count: number;
}

export default function DashboardPage() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedSession, setExpandedSession] = useState<string | null>(null);
  const [sessionLeads, setSessionLeads] = useState<Lead[]>([]);
  const [leadsLoading, setLeadsLoading] = useState(false);

  const fetchSessions = async () => {
    try {
      const res = await fetch(`${api.scrapeUrl.replace("/scrape", "/sessions")}`);
      if (res.ok) {
        const data = await res.json();
        setSessions(data);
      }
    } catch (error) {
      console.error("Failed to fetch sessions", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSessions();
  }, []);

  const handleToggleSession = async (sessionId: string) => {
    if (expandedSession === sessionId) {
      setExpandedSession(null);
      setSessionLeads([]);
      return;
    }

    setExpandedSession(sessionId);
    setLeadsLoading(true);
    setSessionLeads([]);

    try {
      const res = await fetch(api.sessionLeadsUrl(sessionId));
      if (res.ok) {
        const data = await res.json();
        setSessionLeads(data);
      }
    } catch (error) {
      console.error("Failed to fetch session leads", error);
    } finally {
      setLeadsLoading(false);
    }
  };

  const handleDownload = (sessionId: string) => {
    window.open(api.exportUrl(sessionId), "_blank");
  };

  return (
    <div className="relative min-h-screen p-8 bg-[var(--bg-primary)]">
      <div className="relative z-10 max-w-7xl mx-auto space-y-8">
        <header>
          <h1 className="text-3xl font-bold tracking-tight text-[var(--text-primary)]">Dashboard</h1>
          <p className="text-[var(--text-secondary)] text-sm mt-1">Overview of all past scraping sessions and discovered leads.</p>
        </header>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="glass-card rounded-2xl p-6 border border-white/5">
            <p className="text-[10px] font-semibold text-[var(--text-secondary)] uppercase tracking-widest mb-1">Total Sessions</p>
            <p className="text-4xl font-bold text-[var(--text-primary)]">{sessions.length}</p>
          </div>
          <div className="glass-card rounded-2xl p-6 border border-white/5">
            <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-widest mb-1">Total Leads Found</p>
            <p className="text-4xl font-bold bg-gradient-to-r from-cyan-400 to-teal-400 bg-clip-text text-transparent">
              {sessions.reduce((acc, s) => acc + s.lead_count, 0)}
            </p>
          </div>
          <div className="glass-card rounded-2xl p-6 border border-white/5">
            <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-widest mb-1">Avg Leads / Session</p>
            <p className="text-4xl font-bold text-slate-300">
              {sessions.length > 0 ? Math.round(sessions.reduce((acc, s) => acc + s.lead_count, 0) / sessions.length) : 0}
            </p>
          </div>
        </div>

        <div className="glass-card rounded-2xl overflow-hidden border border-white/5">
          <div className="px-6 py-4 border-b border-white/5 bg-white/[0.02] flex items-center justify-between">
            <h2 className="text-lg font-semibold text-white/90">Session History</h2>
            <button
              onClick={fetchSessions}
              className="p-2 rounded-lg hover:bg-white/5 transition-colors text-slate-400"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>
          </div>

          <div>
            {loading ? (
              <div className="p-12 flex justify-center">
                <div className="w-8 h-8 border-2 border-cyan-500/20 border-t-cyan-500 rounded-full animate-spin" />
              </div>
            ) : sessions.length === 0 ? (
              <div className="p-12 text-center text-slate-500">
                No past sessions found. Start a new hunt to see history.
              </div>
            ) : (
              <div className="divide-y divide-white/5">
                {sessions.map((session) => (
                  <div key={session.session_id}>
                    {/* Session Row */}
                    <div
                      className="flex items-center gap-4 px-6 py-4 hover:bg-white/[0.02] transition-colors cursor-pointer group"
                      onClick={() => handleToggleSession(session.session_id)}
                    >
                      <div className="shrink-0">
                        <svg
                          className={`w-4 h-4 text-slate-500 transition-transform duration-200 ${expandedSession === session.session_id ? "rotate-90" : ""}`}
                          fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor"
                        >
                          <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
                        </svg>
                      </div>

                      <div className="flex-1 min-w-0">
                        <p className="text-white/80 font-mono text-xs">{session.session_id}</p>
                      </div>

                      <span className="px-2.5 py-1 rounded-full bg-cyan-500/10 text-cyan-400 font-medium text-xs shrink-0">
                        {session.lead_count} leads
                      </span>

                      <div className="flex gap-2 shrink-0">
                        {session.has_xlsx && (
                          <span className="text-emerald-500/80 text-[10px] font-bold uppercase tracking-widest bg-emerald-500/5 px-2 py-0.5 rounded border border-emerald-500/10">
                            XLSX
                          </span>
                        )}
                        <span className="text-slate-500 text-[10px] font-bold uppercase tracking-widest bg-slate-500/5 px-2 py-0.5 rounded border border-slate-500/10">
                          TXT
                        </span>
                      </div>

                      <button
                        onClick={(e) => { e.stopPropagation(); handleDownload(session.session_id); }}
                        disabled={!session.has_xlsx}
                        className="text-cyan-400 hover:text-cyan-300 disabled:opacity-30 disabled:pointer-events-none transition-colors text-xs font-semibold flex items-center gap-1.5 shrink-0"
                      >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                        </svg>
                        XLSX
                      </button>
                    </div>

                    {/* Expanded LeadTable */}
                    {expandedSession === session.session_id && (
                      <div className="px-4 pb-4 border-t border-white/5 bg-white/[0.01]">
                        {leadsLoading ? (
                          <div className="py-8 flex justify-center">
                            <div className="w-6 h-6 border-2 border-cyan-500/20 border-t-cyan-500 rounded-full animate-spin" />
                          </div>
                        ) : sessionLeads.length === 0 ? (
                          <div className="py-8 text-center text-slate-500 text-sm">
                            No lead data available for this session.
                          </div>
                        ) : (
                          <div className="pt-4 space-y-4">
                            <ExportBar leads={sessionLeads} sessionId={session.session_id} isRunning={false} />
                            <LeadTable leads={sessionLeads} />
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
