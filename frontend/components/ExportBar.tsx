import { Lead } from "@/lib/types";
import { api } from "@/lib/api";
import { useState } from "react";
import * as XLSX from "xlsx";

interface ExportBarProps {
  leads: Lead[];
  sessionId: string | null;
  isRunning: boolean;
}

type ExportFormat = "xlsx" | "csv";
type ExportFilter = "all" | "with-website" | "without-website";

export default function ExportBar({ leads, sessionId, isRunning }: ExportBarProps) {
  const [format, setFormat] = useState<ExportFormat>("xlsx");
  const [filter, setFilter] = useState<ExportFilter>("all");

  const handleClientExport = () => {
    if (leads.length === 0) return;

    let filteredLeads = [...leads];
    if (filter === "with-website") {
      filteredLeads = filteredLeads.filter(l => l.website && l.website.length > 0);
    } else if (filter === "without-website") {
      filteredLeads = filteredLeads.filter(l => !l.website || l.website.length === 0);
    }

    if (filteredLeads.length === 0) {
      alert("No leads match the selected filter.");
      return;
    }

    const exportData = filteredLeads.map((lead, i) => ({
      "#": lead._index || i + 1,
      Name: lead.name || "",
      Rating: lead.rating || "",
      Reviews: lead.reviews || "",
      Phone: lead.phone || "",
      Email: lead.email || "",
      Website: lead.website || "",
      Address: lead.address || "",
      "Plus Code": lead.plus_code || "",
      "Maps URL": lead.maps_url || "",
      Latitude: lead.place_lat ?? "",
      Longitude: lead.place_lng ?? "",
      "Distance (km)": lead.distance_km_from_parent ?? "",
      "Spawn Depth": lead.spawn_depth,
      "Parent Seed": lead.parent_seed_name || "",
      "Root Seed": lead.root_seed_name || "",
      "Scraped At": lead.scraped_at_iso,
    }));

    const ws = XLSX.utils.json_to_sheet(exportData);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Leads");

    if (format === "xlsx") {
      // Auto-size columns for XLSX
      const colWidths = Object.keys(exportData[0]).map((key) => ({
        wch: Math.max(
          key.length,
          ...exportData.map((row) => String((row as Record<string, unknown>)[key] || "").length)
        ),
      }));
      ws["!cols"] = colWidths;
      XLSX.writeFile(wb, `leads-${sessionId || "export"}.xlsx`);
    } else {
      XLSX.writeFile(wb, `leads-${sessionId || "export"}.csv`, { bookType: "csv" });
    }
  };

  const handleServerExport = () => {
    if (!sessionId) return;
    window.open(api.exportUrl(sessionId), "_blank");
  };

  return (
    <div className="glass-card rounded-2xl p-4">
      <div className="flex flex-wrap items-center gap-6">
        <div className="flex items-center gap-2">
          <svg className="w-5 h-5 text-cyan-400" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
          </svg>
          <span className="text-sm font-bold text-[var(--text-primary)] uppercase tracking-tight">Export Tool</span>
        </div>

        <div className="h-8 w-px bg-white/5 hidden md:block" />

        <div className="flex flex-wrap items-center gap-4 flex-1">
          {/* Format Selector */}
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-semibold text-[var(--text-secondary)] uppercase tracking-widest">Format</span>
            <select 
              value={format} 
              onChange={(e) => setFormat(e.target.value as ExportFormat)}
              className="bg-white/5 border border-white/10 rounded-lg text-xs py-1.5 px-3 text-[var(--text-primary)] focus:border-cyan-500 outline-none transition-colors"
            >
              <option value="xlsx">XLSX (Excel)</option>
              <option value="csv">CSV (Comma Separated)</option>
            </select>
          </div>

          {/* Filter Selector */}
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-semibold text-[var(--text-secondary)] uppercase tracking-widest">Include</span>
            <select 
              value={filter} 
              onChange={(e) => setFilter(e.target.value as ExportFilter)}
              className="bg-white/5 border border-white/10 rounded-lg text-xs py-1.5 px-3 text-[var(--text-primary)] focus:border-cyan-500 outline-none transition-colors"
            >
              <option value="all">All Discoveries</option>
              <option value="with-website">With Websites Only</option>
              <option value="without-website">Without Websites Only</option>
            </select>
          </div>
        </div>

        <div className="flex gap-2">
          <button
            onClick={handleClientExport}
            disabled={leads.length === 0}
            className="btn-primary !py-2 !px-4 text-xs font-bold disabled:opacity-30"
          >
            Generate File
          </button>

          {sessionId && (
            <button
              onClick={handleServerExport}
              disabled={isRunning}
              className="btn-secondary !py-2 !px-4 text-xs font-bold disabled:opacity-30"
              title="Download original XLSX from server"
            >
              Server Sync
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
