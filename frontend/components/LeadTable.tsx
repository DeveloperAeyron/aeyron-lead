"use client";

import { Lead } from "@/lib/types";
import { useState } from "react";
import EnrichModal from "./EnrichModal";

interface LeadTableProps {
  leads: Lead[];
}

function DetailRow({ lead }: { lead: Lead }) {
  return (
    <tr className="bg-white/[0.03]">
      <td colSpan={10} className="px-6 py-4">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
          <div>
            <span className="text-[var(--text-secondary)] uppercase tracking-wider">Address</span>
            <p className="text-[var(--text-primary)] mt-0.5">{lead.address || "—"}</p>
          </div>
          <div>
            <span className="text-[var(--text-secondary)] uppercase tracking-wider">Plus Code</span>
            <p className="text-[var(--text-primary)] mt-0.5">{lead.plus_code || "—"}</p>
          </div>
          <div>
            <span className="text-[var(--text-secondary)] uppercase tracking-wider">Coordinates</span>
            <p className="text-[var(--text-primary)] mt-0.5 font-mono">
              {lead.place_lat != null && lead.place_lng != null
                ? `${lead.place_lat.toFixed(6)}, ${lead.place_lng.toFixed(6)}`
                : "—"}
            </p>
          </div>
          <div>
            <span className="text-[var(--text-secondary)] uppercase tracking-wider">Spawn Depth</span>
            <p className="text-[var(--text-primary)] mt-0.5">{lead.spawn_depth}</p>
          </div>
          <div>
            <span className="text-[var(--text-secondary)] uppercase tracking-wider">Parent Seed</span>
            <p className="text-[var(--text-primary)] mt-0.5">{lead.parent_seed_name || "—"}</p>
          </div>
          <div>
            <span className="text-[var(--text-secondary)] uppercase tracking-wider">Root Seed</span>
            <p className="text-[var(--text-primary)] mt-0.5">{lead.root_seed_name || "—"}</p>
          </div>
          <div>
            <span className="text-[var(--text-secondary)] uppercase tracking-wider">Scraped At</span>
            <p className="text-[var(--text-primary)] mt-0.5">{lead.scraped_at_iso}</p>
          </div>
          <div>
            <span className="text-[var(--text-secondary)] uppercase tracking-wider">Maps</span>
            {lead.maps_url ? (
              <a href={lead.maps_url} target="_blank" rel="noopener noreferrer"
                className="text-cyan-400 hover:text-cyan-300 transition-colors mt-0.5 block truncate">
                Open in Maps →
              </a>
            ) : (<p className="text-slate-600 mt-0.5">—</p>)}
          </div>
        </div>
      </td>
    </tr>
  );
}

function LeadRow({ lead, index, isExpanded, onToggle, onEnrich }: {
  lead: Lead; index: number; isExpanded: boolean; onToggle: () => void; onEnrich: () => void;
}) {
  return (
    <>
      <tr onClick={onToggle} className="table-row-hover cursor-pointer animate-slide-in"
        style={{ animationDelay: `${Math.min(index * 30, 300)}ms` }}>
        <td className="table-cell text-center text-[var(--text-secondary)] font-mono text-xs">{lead._index || index + 1}</td>
        <td className="table-cell font-medium text-[var(--text-primary)] max-w-[200px] truncate">{lead.name || "—"}</td>
        <td className="table-cell">
          {lead.rating ? (
            <span className="inline-flex items-center gap-1">
              <svg className="w-3.5 h-3.5 text-amber-400" fill="currentColor" viewBox="0 0 20 20">
                <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
              </svg>
              <span className="text-amber-300/80">{lead.rating}</span>
            </span>
          ) : <span className="text-[var(--text-secondary)]">—</span>}
        </td>
        <td className="table-cell text-[var(--text-secondary)]">{lead.reviews || "—"}</td>
        <td className="table-cell">
          {lead.phone ? (
            <a href={`tel:${lead.phone}`} onClick={e => e.stopPropagation()} className="text-cyan-400 hover:text-cyan-300 transition-colors">{lead.phone}</a>
          ) : <span className="text-[var(--text-secondary)]">—</span>}
        </td>
        <td className="table-cell">
          {lead.email ? (
            <a href={`mailto:${lead.email}`} onClick={e => e.stopPropagation()} className="text-teal-400 hover:text-teal-300 transition-colors max-w-[160px] truncate block">{lead.email}</a>
          ) : <span className="text-[var(--text-secondary)]">—</span>}
        </td>
        <td className="table-cell">
          <div className="flex items-center gap-1.5">
            {lead.website ? (
              <>
                <a href={lead.website.startsWith("http") ? lead.website : `https://${lead.website}`} target="_blank" rel="noopener noreferrer" onClick={e => e.stopPropagation()} className="text-indigo-400 hover:text-indigo-300 transition-colors max-w-[120px] truncate block">{lead.website}</a>
                <button
                  onClick={(e) => { e.stopPropagation(); onEnrich(); }}
                  className="shrink-0 w-6 h-6 rounded-md bg-cyan-500/10 hover:bg-cyan-500/25 border border-cyan-500/20 hover:border-cyan-500/40 flex items-center justify-center transition-all"
                  title="Scan for emails & socials"
                >
                  <svg className="w-3 h-3 text-cyan-400" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
                  </svg>
                </button>
              </>
            ) : <span className="text-[var(--text-secondary)]">—</span>}
          </div>
        </td>
        <td className="table-cell text-[var(--text-secondary)] max-w-[200px] truncate hidden lg:table-cell">{lead.address || "—"}</td>
        <td className="table-cell text-right font-mono text-[var(--text-secondary)] hidden md:table-cell">
          {lead.distance_km_from_parent != null ? lead.distance_km_from_parent.toFixed(2) : "—"}
        </td>
      </tr>
      {isExpanded && <DetailRow lead={lead} />}
    </>
  );
}

export default function LeadTable({ leads }: LeadTableProps) {
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);
  const [enrichTarget, setEnrichTarget] = useState<{ url: string; name: string } | null>(null);

  if (leads.length === 0) {
    return (
      <div className="glass-card rounded-2xl p-12 text-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-16 h-16 rounded-2xl bg-slate-800/60 flex items-center justify-center">
            <svg className="w-8 h-8 text-[var(--text-secondary)]" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z" />
            </svg>
          </div>
          <p className="text-[var(--text-secondary)] font-medium">No leads yet</p>
          <p className="text-[var(--text-secondary)] text-sm">Start a scrape to discover leads in real-time</p>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="glass-card rounded-2xl overflow-hidden">
        <div className="flex items-center gap-3 px-6 py-4 border-b border-white/5">
          <div className="h-6 w-1 rounded-full bg-gradient-to-b from-cyan-400 to-teal-500" />
          <h2 className="text-lg font-semibold text-[var(--text-primary)] tracking-tight">Discovered Leads</h2>
          <span className="ml-auto text-xs font-medium text-[var(--text-secondary)] bg-slate-800/80 px-3 py-1 rounded-full">{leads.length} total</span>
        </div>
        <div className="overflow-x-auto max-h-[600px] overflow-y-auto scrollbar-thin">
          <table className="w-full text-sm" id="leads-table">
            <thead className="sticky top-0 z-10">
              <tr className="bg-[var(--bg-secondary)] backdrop-blur-sm border-b border-[var(--border-subtle)]">
                <th className="table-header w-12">#</th>
                <th className="table-header text-left">Name</th>
                <th className="table-header text-left">Rating</th>
                <th className="table-header text-left">Reviews</th>
                <th className="table-header text-left">Phone</th>
                <th className="table-header text-left">Email</th>
                <th className="table-header text-left">Website</th>
                <th className="table-header text-left hidden lg:table-cell">Address</th>
                <th className="table-header text-right hidden md:table-cell">Dist (km)</th>
              </tr>
            </thead>
            <tbody>
              {leads.map((lead, i) => (
                <LeadRow
                  key={i}
                  lead={lead}
                  index={i}
                  isExpanded={expandedIndex === i}
                  onToggle={() => setExpandedIndex(expandedIndex === i ? null : i)}
                  onEnrich={() => setEnrichTarget({ url: lead.website || "", name: lead.name || "Unknown" })}
                />
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {enrichTarget && (
        <EnrichModal
          websiteUrl={enrichTarget.url}
          leadName={enrichTarget.name}
          onClose={() => setEnrichTarget(null)}
        />
      )}
    </>
  );
}
