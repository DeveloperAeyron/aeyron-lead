"use client";

import { useCallback, useRef, useState } from "react";
import ControlPanel from "@/components/ControlPanel";
import StatsBar from "@/components/StatsBar";
import LeadTable from "@/components/LeadTable";
import ExportBar from "@/components/ExportBar";
import LogPanel from "@/components/LogPanel";
import { Lead, ScrapeConfig, ScrapeStatus } from "@/lib/types";
import { api } from "@/lib/api";

export default function LeadHuntPage() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [status, setStatus] = useState<ScrapeStatus>("idle");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [startTime, setStartTime] = useState<number | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [showLogs, setShowLogs] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const handleStart = useCallback(async (config: ScrapeConfig) => {
    setLeads([]);
    setLogs([]);
    setStatus("running");
    setStartTime(Date.now());
    setSessionId(null);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const res = await fetch(api.scrapeUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config),
        signal: controller.signal,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || "Failed to start scrape");
      }

      const reader = res.body?.getReader();
      if (!reader) throw new Error("No response stream");

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        let currentEvent = "";
        for (const line of lines) {
          if (line.startsWith("event:")) {
            currentEvent = line.slice(6).trim();
          } else if (line.startsWith("data:")) {
            const dataStr = line.slice(5).trim();
            try {
              const data = JSON.parse(dataStr);
              switch (currentEvent) {
                case "session_start":
                  setSessionId(data.session_id);
                  break;
                case "lead":
                  setLeads((prev) => {
                    const incoming = data as Lead;
                    const key = incoming.maps_url || `${incoming.name}|${incoming.address}|${incoming.phone}`;
                    const exists = prev.some((l) => {
                      const lKey = l.maps_url || `${l.name}|${l.address}|${l.phone}`;
                      return lKey === key;
                    });
                    return exists ? prev : [...prev, incoming];
                  });
                  break;
                case "log":
                  setLogs((prev) => [...prev.slice(-200), data.message]);
                  break;
                case "complete":
                  setStatus("complete");
                  setSessionId(data.session_id);
                  break;
              }
            } catch { /* skip */ }
            currentEvent = "";
          }
        }
      }
      setStatus((prev) => (prev === "running" ? "complete" : prev));
    } catch (err: unknown) {
      if (err instanceof Error && err.name === "AbortError") {
        setStatus("stopped");
      } else {
        setStatus("error");
        setLogs((prev) => [...prev, `Error: ${err instanceof Error ? err.message : String(err)}`]);
      }
    }
  }, []);

  const handleStop = useCallback(async () => {
    abortRef.current?.abort();
    try {
      await fetch(api.stopUrl, { method: "POST" });
    } catch { /* best effort */ }
    setStatus("stopped");
  }, []);

  return (
    <div className="relative min-h-screen bg-[var(--bg-primary)]">
      <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        <header className="flex flex-col gap-1 mb-2">
          <h1 className="text-3xl font-bold tracking-tight text-[var(--text-primary)]">Lead Hunt</h1>
          <p className="text-[var(--text-secondary)] text-sm">Start a new discovery session to find leads in real-time.</p>
        </header>

        <ControlPanel onStart={handleStart} onStop={handleStop} isRunning={status === "running"} />
        <StatsBar leadCount={leads.length} status={status} startTime={startTime} sessionId={sessionId} />
        <ExportBar leads={leads} sessionId={sessionId} isRunning={status === "running"} />
        <LeadTable leads={leads} />
        <LogPanel logs={logs} isVisible={showLogs} onToggle={() => setShowLogs(!showLogs)} />
      </div>
    </div>
  );
}
