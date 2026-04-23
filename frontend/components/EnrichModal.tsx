"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface EnrichResult {
  emails: string[];
  socials: Record<string, string[]>;
  pages_checked: string[];
  error?: string;
}

const SOCIAL_ICONS: Record<string, string> = {
  facebook: "📘",
  instagram: "📸",
  twitter: "🐦",
  linkedin: "💼",
  youtube: "🎬",
  tiktok: "🎵",
  pinterest: "📌",
  yelp: "⭐",
};

interface EnrichModalProps {
  websiteUrl: string;
  leadName: string;
  onClose: () => void;
}

export default function EnrichModal({ websiteUrl, leadName, onClose }: EnrichModalProps) {
  const [result, setResult] = useState<EnrichResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Auto-fetch on mount
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(api.enrichUrl, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url: websiteUrl }),
        });
        const data = await res.json();
        if (cancelled) return;
        if (data.error) setError(data.error);
        setResult(data);
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Failed to enrich");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [websiteUrl]);

  const socialEntries = result?.socials ? Object.entries(result.socials).filter(([, urls]) => urls.length > 0) : [];
  const hasData = result && (result.emails.length > 0 || socialEntries.length > 0);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={onClose}>
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" />

      {/* Modal */}
      <div
        className="relative w-full max-w-lg glass-card rounded-2xl overflow-hidden animate-slide-in"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/5">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-cyan-500/20 to-teal-500/20 flex items-center justify-center shrink-0">
              <svg className="w-4.5 h-4.5 text-cyan-400" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 017.843 4.582M12 3a8.997 8.997 0 00-7.843 4.582m15.686 0A11.953 11.953 0 0112 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0121 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0112 16.5a17.92 17.92 0 01-8.716-2.247m0 0A9.015 9.015 0 003 12c0-1.605.42-3.113 1.157-4.418" />
              </svg>
            </div>
            <div className="min-w-0">
              <h3 className="text-sm font-bold text-[var(--text-primary)] truncate">{leadName}</h3>
              <p className="text-[10px] text-[var(--text-secondary)] truncate">{websiteUrl}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg bg-white/5 hover:bg-white/10 flex items-center justify-center transition-colors shrink-0"
          >
            <svg className="w-4 h-4 text-[var(--text-secondary)]" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-5 max-h-[60vh] overflow-y-auto">
          {loading ? (
            <div className="flex flex-col items-center gap-3 py-8">
              <div className="w-8 h-8 border-2 border-cyan-400/30 border-t-cyan-400 rounded-full animate-spin" />
              <p className="text-sm text-[var(--text-secondary)]">Scanning website...</p>
              <p className="text-[10px] text-[var(--text-secondary)]">Checking homepage, contact & about pages</p>
            </div>
          ) : error && !hasData ? (
            <div className="text-center py-8">
              <p className="text-red-400 text-sm font-medium">Failed to scan</p>
              <p className="text-[var(--text-secondary)] text-xs mt-1">{error}</p>
            </div>
          ) : !hasData ? (
            <div className="text-center py-8">
              <p className="text-[var(--text-secondary)] text-sm">No emails or socials found on this website.</p>
              <p className="text-[var(--text-secondary)] text-xs mt-1">
                Checked {result?.pages_checked.length || 0} page(s)
              </p>
            </div>
          ) : (
            <div className="space-y-5">
              {/* Emails */}
              {result!.emails.length > 0 && (
                <div>
                  <h4 className="text-[10px] font-bold text-[var(--text-secondary)] uppercase tracking-widest mb-2">
                    📧 Emails Found ({result!.emails.length})
                  </h4>
                  <div className="space-y-1.5">
                    {result!.emails.map((email, i) => (
                      <div key={i} className="flex items-center gap-2 bg-white/[0.03] rounded-lg px-3 py-2">
                        <a
                          href={`mailto:${email}`}
                          className="text-sm text-cyan-400 hover:text-cyan-300 transition-colors truncate"
                        >
                          {email}
                        </a>
                        <button
                          onClick={() => navigator.clipboard.writeText(email)}
                          className="ml-auto text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors shrink-0"
                          title="Copy"
                        >
                          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M15.666 3.888A2.25 2.25 0 0013.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 01-.75.75H9.75a.75.75 0 01-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 01-2.25 2.25H6.75A2.25 2.25 0 014.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 011.927-.184" />
                          </svg>
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Socials */}
              {socialEntries.length > 0 && (
                <div>
                  <h4 className="text-[10px] font-bold text-[var(--text-secondary)] uppercase tracking-widest mb-2">
                    🔗 Social Profiles ({socialEntries.reduce((s, [, u]) => s + u.length, 0)})
                  </h4>
                  <div className="space-y-1.5">
                    {socialEntries.map(([platform, urls]) =>
                      urls.map((url, i) => (
                        <div key={`${platform}-${i}`} className="flex items-center gap-2.5 bg-white/[0.03] rounded-lg px-3 py-2">
                          <span className="text-base">{SOCIAL_ICONS[platform] || "🌐"}</span>
                          <div className="min-w-0 flex-1">
                            <span className="text-[10px] font-semibold text-[var(--text-secondary)] uppercase">{platform}</span>
                            <a
                              href={url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-sm text-indigo-400 hover:text-indigo-300 transition-colors block truncate"
                            >
                              {url.replace(/https?:\/\/(www\.)?/, "")}
                            </a>
                          </div>
                          <button
                            onClick={() => navigator.clipboard.writeText(url)}
                            className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors shrink-0"
                            title="Copy"
                          >
                            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" d="M15.666 3.888A2.25 2.25 0 0013.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 01-.75.75H9.75a.75.75 0 01-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 01-2.25 2.25H6.75A2.25 2.25 0 014.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 011.927-.184" />
                            </svg>
                          </button>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              )}

              {/* Pages Checked */}
              <div className="pt-2 border-t border-white/5">
                <p className="text-[10px] text-[var(--text-secondary)]">
                  Scanned {result!.pages_checked.length} page(s)
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
