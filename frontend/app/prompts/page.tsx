"use client";

import { useCallback, useEffect, useState } from "react";
import { api, withApiHeaders } from "@/lib/api";

interface PromptPayload {
  system_prompt_template: string;
}

export default function PromptsPage() {
  const [current, setCurrent] = useState<PromptPayload | null>(null);
  const [defaults, setDefaults] = useState<PromptPayload | null>(null);
  const [editing, setEditing] = useState<PromptPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

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

      <div className="glass-card rounded-2xl border border-[var(--border-subtle)] p-6 md:p-8 space-y-3">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold text-[var(--text-primary)] uppercase tracking-wider">
              System prompt (single block)
            </h2>
            <p className="text-xs text-[var(--text-secondary)] mt-1">
              This is the exact system prompt template sent to the model. Keep the token{" "}
              <span className="font-mono text-[var(--text-primary)]">{`{OUTPUT_CONTRACT_JSON}`}</span>{" "}
              somewhere in the text — it will be replaced at runtime with the required JSON output schema.
            </p>
          </div>
          {defaults && current && current.system_prompt_template !== defaults.system_prompt_template ? (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-400 font-medium">
              Modified
            </span>
          ) : null}
        </div>

        {editing ? (
          <textarea
            value={editing.system_prompt_template}
            onChange={(e) =>
              setEditing((prev) => (prev ? { ...prev, system_prompt_template: e.target.value } : prev))
            }
            rows={22}
            className="w-full rounded-xl bg-black/30 border border-[var(--border-subtle)] p-4 text-sm text-[var(--text-primary)] font-mono resize-y focus:outline-none focus:ring-2 focus:ring-purple-500/40 focus:border-purple-500/40 scrollbar-thin placeholder:text-[var(--text-secondary)]/40"
            spellCheck={false}
          />
        ) : null}

        {defaults && (
          <button
            type="button"
            onClick={() =>
              setEditing((prev) =>
                prev ? { ...prev, system_prompt_template: defaults.system_prompt_template } : prev,
              )
            }
            className="text-xs text-amber-400 hover:text-amber-300 font-medium"
          >
            Revert to default
          </button>
        )}
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
