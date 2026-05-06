"use client";

import { useCallback, useEffect, useState } from "react";
import { api, withApiHeaders } from "@/lib/api";

interface PromptSections {
  product_portfolio: string;
  non_negotiable_rules: string;
  tone_anchor: string;
}

const SECTION_META: { key: keyof PromptSections; label: string; description: string }[] = [
  {
    key: "product_portfolio",
    label: "Product Portfolio",
    description:
      "The product catalogue injected into the system prompt. The model picks at most one product per email.",
  },
  {
    key: "non_negotiable_rules",
    label: "Non-Negotiable Rules",
    description:
      "Hard constraints the model must follow: subject line style, word limits, forbidden words, CTA shape, etc.",
  },
  {
    key: "tone_anchor",
    label: "Tone Anchor (Example)",
    description:
      "A fictional example email that anchors the model's style. It imitates structure, not wording.",
  },
];

export default function PromptsPage() {
  const [current, setCurrent] = useState<PromptSections | null>(null);
  const [defaults, setDefaults] = useState<PromptSections | null>(null);
  const [editing, setEditing] = useState<PromptSections | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [expandedSection, setExpandedSection] = useState<keyof PromptSections | null>(null);

  const fetchPrompts = useCallback(async () => {
    setError(null);
    try {
      const res = await fetch(api.promptsUrl, withApiHeaders());
      if (!res.ok) throw new Error(`Failed to load prompts (${res.status})`);
      const data = await res.json();
      setCurrent(data.current);
      setDefaults(data.defaults);
      setEditing(data.current);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load prompts.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPrompts();
  }, [fetchPrompts]);

  const handleSave = async () => {
    if (!editing) return;
    setSaving(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const res = await fetch(
        api.promptsUrl,
        withApiHeaders({
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(editing),
        }),
      );
      if (!res.ok) throw new Error(`Save failed (${res.status})`);
      const data = await res.json();
      setCurrent(data.current);
      setEditing(data.current);
      setSuccessMsg("Prompts saved successfully. Changes apply to all future generations.");
      setTimeout(() => setSuccessMsg(null), 4000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed.");
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    if (!confirm("Reset all prompt sections to their original defaults? This cannot be undone.")) return;
    setSaving(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const res = await fetch(
        api.promptsResetUrl,
        withApiHeaders({ method: "POST" }),
      );
      if (!res.ok) throw new Error(`Reset failed (${res.status})`);
      const data = await res.json();
      setCurrent(data.current);
      setEditing(data.current);
      setSuccessMsg("Prompts reset to defaults.");
      setTimeout(() => setSuccessMsg(null), 4000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reset failed.");
    } finally {
      setSaving(false);
    }
  };

  const hasChanges =
    editing && current && JSON.stringify(editing) !== JSON.stringify(current);

  const isModifiedFromDefault = (key: keyof PromptSections) =>
    defaults && current && current[key] !== defaults[key];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="w-10 h-10 border-2 border-cyan-400/30 border-t-cyan-400 rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="p-6 md:p-10 max-w-5xl mx-auto space-y-8 pb-24">
      <header className="space-y-2">
        <div className="flex items-center gap-3">
          <div className="h-8 w-1 rounded-full bg-gradient-to-b from-purple-400 to-pink-500" />
          <h1 className="text-2xl font-semibold text-[var(--text-primary)] tracking-tight">
            Prompt Management
          </h1>
        </div>
        <p className="text-sm text-[var(--text-secondary)] max-w-2xl">
          View and edit the system prompt sections used for email generation. Changes are saved
          server-side and apply to all subsequent single and batch generations.
        </p>
      </header>

      {error && (
        <div className="text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3">
          {error}
        </div>
      )}

      {successMsg && (
        <div className="text-sm text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 rounded-xl px-4 py-3">
          {successMsg}
        </div>
      )}

      <div className="space-y-6">
        {SECTION_META.map(({ key, label, description }) => {
          const isExpanded = expandedSection === key;
          const modified = isModifiedFromDefault(key);

          return (
            <div
              key={key}
              className="glass-card rounded-2xl border border-[var(--border-subtle)] overflow-hidden"
            >
              <button
                type="button"
                onClick={() => setExpandedSection(isExpanded ? null : key)}
                className="w-full flex items-center justify-between p-5 md:p-6 text-left hover:bg-white/[0.02] transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-purple-500/15 text-purple-400">
                    <svg
                      className="w-4 h-4"
                      fill="none"
                      viewBox="0 0 24 24"
                      strokeWidth={1.5}
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"
                      />
                    </svg>
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-[var(--text-primary)]">{label}</span>
                      {modified && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-400 font-medium">
                          Modified
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-[var(--text-secondary)] mt-0.5">{description}</p>
                  </div>
                </div>
                <svg
                  className={`w-5 h-5 text-[var(--text-secondary)] transition-transform ${
                    isExpanded ? "rotate-180" : ""
                  }`}
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth={1.5}
                  stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
                </svg>
              </button>

              {isExpanded && editing && (
                <div className="px-5 md:px-6 pb-5 md:pb-6 space-y-3">
                  <textarea
                    value={editing[key]}
                    onChange={(e) =>
                      setEditing((prev) => (prev ? { ...prev, [key]: e.target.value } : prev))
                    }
                    rows={16}
                    className="w-full rounded-xl bg-black/30 border border-[var(--border-subtle)] p-4 text-sm text-[var(--text-primary)] font-mono resize-y focus:outline-none focus:ring-2 focus:ring-purple-500/40 focus:border-purple-500/40 scrollbar-thin placeholder:text-[var(--text-secondary)]/40"
                    spellCheck={false}
                  />
                  {modified && defaults && (
                    <button
                      type="button"
                      onClick={() =>
                        setEditing((prev) =>
                          prev ? { ...prev, [key]: defaults[key] } : prev,
                        )
                      }
                      className="text-xs text-amber-400 hover:text-amber-300 font-medium"
                    >
                      Revert this section to default
                    </button>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="flex flex-wrap items-center gap-3 pt-2">
        <button
          type="button"
          onClick={handleSave}
          disabled={saving || !hasChanges}
          className="px-6 py-3 rounded-xl font-semibold text-sm bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 text-white shadow-lg shadow-purple-500/20 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
        >
          {saving ? (
            <span className="inline-flex items-center gap-2">
              <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              Saving…
            </span>
          ) : (
            "Save changes"
          )}
        </button>

        <button
          type="button"
          onClick={handleReset}
          disabled={saving}
          className="px-5 py-3 rounded-xl font-semibold text-sm border border-[var(--border-subtle)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-red-500/30 hover:bg-red-500/5 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
        >
          Reset all to defaults
        </button>

        {hasChanges && (
          <span className="text-xs text-amber-400 ml-auto">Unsaved changes</span>
        )}
      </div>
    </div>
  );
}
