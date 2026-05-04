"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { EmailDraftResult, Lead, SessionListItem } from "@/lib/types";

async function detailFromResponse(res: Response): Promise<string> {
  try {
    const j = await res.json();
    if (typeof j.detail === "string") return j.detail;
    if (Array.isArray(j.detail)) {
      return j.detail
        .map((x: { msg?: string }) => (typeof x.msg === "string" ? x.msg : JSON.stringify(x)))
        .join("; ");
    }
    return res.statusText;
  } catch {
    return res.statusText;
  }
}

export default function OutreachPage() {
  const [companyName, setCompanyName] = useState("");
  const [doResearch, setDoResearch] = useState(true);
  const [showMoreOptions, setShowMoreOptions] = useState(false);

  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [position, setPosition] = useState("");
  const [industry, setIndustry] = useState("");
  const [additionalContext, setAdditionalContext] = useState("");
  const [newsJson, setNewsJson] = useState("");
  const [showOllama, setShowOllama] = useState(false);
  const [model, setModel] = useState("qwen2.5:3b");
  const [ollamaUrl, setOllamaUrl] = useState("http://localhost:11434");
  const [temperature, setTemperature] = useState(0.25);
  const [timeoutS, setTimeoutS] = useState(300);

  const [sessions, setSessions] = useState<SessionListItem[]>([]);
  const [sessionId, setSessionId] = useState("");
  const [sessionLeads, setSessionLeads] = useState<Lead[]>([]);
  const [leadIndex, setLeadIndex] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<EmailDraftResult | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(api.sessionsUrl);
        if (!res.ok || cancelled) return;
        const list = (await res.json()) as SessionListItem[];
        if (!cancelled) setSessions(Array.isArray(list) ? list : []);
      } catch {
        /* optional prefill */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!sessionId) return;
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(api.sessionLeadsUrl(sessionId));
        if (!res.ok || cancelled) return;
        const leads = (await res.json()) as Lead[];
        if (!cancelled) {
          setSessionLeads(Array.isArray(leads) ? leads : []);
          setLeadIndex("");
        }
      } catch {
        if (!cancelled) setSessionLeads([]);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  const applyLead = useCallback((idx: number) => {
    const lead = sessionLeads[idx];
    if (!lead) return;
    setCompanyName(lead.name?.trim() || "");
    setFirstName("");
    setLastName("");
    setEmail(lead.email?.trim() || "");
    setPosition("");
    setIndustry("");
    setLeadIndex(String(idx));
  }, [sessionLeads]);

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setResult(null);

    let newsReport: Record<string, unknown> | undefined;
    const rawJson = newsJson.trim();
    if (rawJson) {
      try {
        const parsed = JSON.parse(rawJson) as unknown;
        if (parsed !== null && typeof parsed === "object" && !Array.isArray(parsed)) {
          newsReport = parsed as Record<string, unknown>;
        } else {
          setError("News report JSON must be an object.");
          return;
        }
      } catch {
        setError("News report JSON could not be parsed.");
        return;
      }
    }

    setLoading(true);
    try {
      const body = {
        company_name: companyName.trim(),
        email: email.trim(),
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        position: position.trim(),
        industry: industry.trim(),
        news_report: newsReport,
        additional_context: additionalContext.trim(),
        do_research: newsReport ? false : doResearch,
        model: model.trim(),
        ollama_url: ollamaUrl.trim(),
        temperature,
        timeout_s: timeoutS,
      };
      const res = await fetch(api.generateEmailUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        throw new Error(await detailFromResponse(res));
      }
      const data = (await res.json()) as EmailDraftResult;
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generation failed.");
    } finally {
      setLoading(false);
    }
  };

  const copy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      /* ignore */
    }
  };

  const copyFullCampaign = async () => {
    if (!result) return;
    const block = [`Subject: ${result.subject}`, "", result.email_body].join("\n");
    await copy(block);
  };

  return (
    <div className="p-6 md:p-10 max-w-5xl mx-auto space-y-8 pb-24">
      <header className="space-y-2">
        <div className="flex items-center gap-3">
          <div className="h-8 w-1 rounded-full bg-gradient-to-b from-cyan-400 to-teal-500" />
          <h1 className="text-2xl font-semibold text-[var(--text-primary)] tracking-tight">
            Email campaigns
          </h1>
        </div>
        <p className="text-sm text-[var(--text-secondary)] max-w-2xl">
          Enter a <span className="text-[var(--text-primary)]">company name</span> and generate a personalised email
          campaign. We research the company automatically (same as the backend CLI without{" "}
          <code className="text-cyan-400/90 text-xs">--no-research</code>), then call your local{" "}
          <span className="text-[var(--text-primary)]">Ollama</span> model. The first run can take several minutes.
        </p>
      </header>

      <form onSubmit={handleGenerate} className="glass-card rounded-2xl p-6 md:p-8 space-y-6">
        <div className="space-y-2">
          <label htmlFor="company" className="text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider">
            Company name
          </label>
          <input
            id="company"
            type="text"
            value={companyName}
            onChange={(e) => setCompanyName(e.target.value)}
            className="input-field text-lg py-3"
            placeholder="e.g. Acme Corporation"
            autoComplete="organization"
            required
          />
        </div>

        <button
          type="submit"
          disabled={loading || !companyName.trim()}
          className="w-full py-3.5 rounded-xl font-semibold text-sm bg-gradient-to-r from-cyan-600 to-teal-600 hover:from-cyan-500 hover:to-teal-500 text-white shadow-lg shadow-cyan-500/20 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
        >
          {loading ? (
            <span className="inline-flex items-center justify-center gap-2">
              <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              {doResearch && !newsJson.trim()
                ? "Researching company and generating campaign…"
                : "Generating email campaign…"}
            </span>
          ) : (
            "Generate email campaign"
          )}
        </button>

        <button
          type="button"
          onClick={() => setShowMoreOptions((v) => !v)}
          className="text-xs font-medium text-cyan-400 hover:text-cyan-300"
        >
          {showMoreOptions ? "Hide" : "Show"} optional settings
        </button>

        {showMoreOptions && (
          <div className="space-y-6 pt-2 border-t border-[var(--border-subtle)]">
            <label className="flex items-start gap-3 cursor-pointer group">
              <input
                type="checkbox"
                checked={doResearch}
                onChange={(e) => setDoResearch(e.target.checked)}
                disabled={!!newsJson.trim()}
                className="mt-1 rounded border-[var(--border-subtle)] disabled:opacity-40"
              />
              <span className="text-sm text-[var(--text-secondary)] group-hover:text-[var(--text-primary)] transition-colors">
                Run live company research before drafting (recommended). Turn off only for quick tests without search.
                Disabled when pasted news JSON is present.
              </span>
            </label>

            <div className="space-y-3 p-4 rounded-xl bg-white/[0.03] border border-[var(--border-subtle)]">
              <p className="text-xs text-[var(--text-secondary)]">Prefill company from Lead Hunt</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <label className="text-[10px] font-medium text-[var(--text-secondary)] uppercase tracking-wider">
                    Session
                  </label>
                  <select
                    value={sessionId}
                    onChange={(e) => {
                      const id = e.target.value;
                      setSessionId(id);
                      if (!id) {
                        setSessionLeads([]);
                        setLeadIndex("");
                      }
                    }}
                    className="input-field"
                  >
                    <option value="">None</option>
                    {sessions.map((s) => (
                      <option key={s.session_id} value={s.session_id}>
                        {s.session_id} ({s.lead_count} leads)
                      </option>
                    ))}
                  </select>
                </div>
                <div className="space-y-1.5">
                  <label className="text-[10px] font-medium text-[var(--text-secondary)] uppercase tracking-wider">
                    Lead
                  </label>
                  <select
                    value={leadIndex}
                    onChange={(e) => {
                      const v = e.target.value;
                      setLeadIndex(v);
                      if (v !== "") applyLead(Number(v));
                    }}
                    className="input-field"
                    disabled={sessionLeads.length === 0}
                  >
                    <option value="">Select…</option>
                    {sessionLeads.map((lead, idx) => (
                      <option key={idx} value={idx}>
                        {(lead.name || "Unnamed") + (lead.address ? ` — ${lead.address}` : "")}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-[10px] font-medium text-[var(--text-secondary)] uppercase tracking-wider">
                  First name
                </label>
                <input value={firstName} onChange={(e) => setFirstName(e.target.value)} className="input-field" />
              </div>
              <div className="space-y-1.5">
                <label className="text-[10px] font-medium text-[var(--text-secondary)] uppercase tracking-wider">
                  Last name
                </label>
                <input value={lastName} onChange={(e) => setLastName(e.target.value)} className="input-field" />
              </div>
              <div className="space-y-1.5">
                <label className="text-[10px] font-medium text-[var(--text-secondary)] uppercase tracking-wider">
                  Email
                </label>
                <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} className="input-field" />
              </div>
              <div className="space-y-1.5">
                <label className="text-[10px] font-medium text-[var(--text-secondary)] uppercase tracking-wider">
                  Role / title
                </label>
                <input value={position} onChange={(e) => setPosition(e.target.value)} className="input-field" />
              </div>
              <div className="space-y-1.5 sm:col-span-2">
                <label className="text-[10px] font-medium text-[var(--text-secondary)] uppercase tracking-wider">
                  Industry
                </label>
                <input value={industry} onChange={(e) => setIndustry(e.target.value)} className="input-field" />
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="text-[10px] font-medium text-[var(--text-secondary)] uppercase tracking-wider">
                Extra context (optional)
              </label>
              <textarea
                value={additionalContext}
                onChange={(e) => setAdditionalContext(e.target.value)}
                rows={3}
                className="input-field resize-y text-sm"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-[10px] font-medium text-[var(--text-secondary)] uppercase tracking-wider">
                News JSON (optional — skips live research when valid)
              </label>
              <textarea
                value={newsJson}
                onChange={(e) => setNewsJson(e.target.value)}
                rows={4}
                className="input-field resize-y font-mono text-xs"
              />
            </div>

            <button
              type="button"
              onClick={() => setShowOllama((v) => !v)}
              className="text-xs font-medium text-cyan-400 hover:text-cyan-300"
            >
              {showOllama ? "Hide" : "Show"} Ollama connection
            </button>
            {showOllama && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1.5 sm:col-span-2">
                  <label className="text-[10px] font-medium text-[var(--text-secondary)] uppercase tracking-wider">
                    Ollama URL
                  </label>
                  <input value={ollamaUrl} onChange={(e) => setOllamaUrl(e.target.value)} className="input-field font-mono text-sm" />
                </div>
                <div className="space-y-1.5">
                  <label className="text-[10px] font-medium text-[var(--text-secondary)] uppercase tracking-wider">
                    Model
                  </label>
                  <input value={model} onChange={(e) => setModel(e.target.value)} className="input-field font-mono text-sm" />
                </div>
                <div className="space-y-1.5">
                  <label className="text-[10px] font-medium text-[var(--text-secondary)] uppercase tracking-wider">
                    Temperature
                  </label>
                  <input
                    type="number"
                    step={0.05}
                    min={0}
                    max={2}
                    value={temperature}
                    onChange={(e) => setTemperature(parseFloat(e.target.value) || 0)}
                    className="input-field"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-[10px] font-medium text-[var(--text-secondary)] uppercase tracking-wider">
                    Timeout (s)
                  </label>
                  <input
                    type="number"
                    min={30}
                    max={1200}
                    value={timeoutS}
                    onChange={(e) => setTimeoutS(parseInt(e.target.value, 10) || 300)}
                    className="input-field"
                  />
                </div>
              </div>
            )}
          </div>
        )}

        {error && (
          <div className="text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3">
            {error}
          </div>
        )}
      </form>

      <div className="glass-card rounded-2xl p-6 md:p-8 min-h-[200px] space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-sm font-semibold text-[var(--text-primary)] uppercase tracking-wider">Email campaign</h2>
          {result && !loading ? (
            <button
              type="button"
              onClick={() => copyFullCampaign()}
              className="text-xs font-medium text-cyan-400 hover:text-cyan-300"
            >
              Copy subject &amp; body
            </button>
          ) : null}
        </div>
        {!result && !loading && (
          <p className="text-sm text-[var(--text-secondary)]">Your subject line and message will appear here.</p>
        )}
        {loading && (
          <div className="flex flex-col items-center justify-center gap-3 py-12 text-[var(--text-secondary)] text-sm">
            <div className="w-10 h-10 border-2 border-cyan-400/30 border-t-cyan-400 rounded-full animate-spin" />
            Usually one to several minutes whilst research and generation run.
          </div>
        )}
        {result && !loading && (
          <div className="space-y-5 animate-slide-in">
            <div className="flex flex-wrap gap-2 text-[11px] text-[var(--text-secondary)]">
              <span
                className={`px-2 py-0.5 rounded-md border ${
                  result.research_used ? "border-cyan-500/40 text-cyan-400" : "border-white/10"
                }`}
              >
                {result.research_used ? "Company research included" : "Research skipped or from pasted JSON"}
              </span>
              {result.confidence ? (
                <span className="px-2 py-0.5 rounded-md border border-white/10">Confidence: {result.confidence}</span>
              ) : null}
            </div>

            <div>
              <div className="flex justify-between items-center mb-1.5">
                <span className="text-[10px] font-medium text-[var(--text-secondary)] uppercase tracking-wider">
                  Subject line
                </span>
                <button type="button" onClick={() => copy(result.subject)} className="text-[10px] text-cyan-400 hover:text-cyan-300">
                  Copy
                </button>
              </div>
              <p className="text-[var(--text-primary)] font-semibold">{result.subject || "—"}</p>
            </div>

            <div>
              <div className="flex justify-between items-center mb-1.5">
                <span className="text-[10px] font-medium text-[var(--text-secondary)] uppercase tracking-wider">
                  Message body
                </span>
                <button type="button" onClick={() => copy(result.email_body)} className="text-[10px] text-cyan-400 hover:text-cyan-300">
                  Copy
                </button>
              </div>
              <pre className="whitespace-pre-wrap text-sm text-[var(--text-primary)] bg-black/20 rounded-xl p-4 border border-[var(--border-subtle)] max-h-[min(70vh,520px)] overflow-y-auto scrollbar-thin">
                {result.email_body || "—"}
              </pre>
            </div>

            {(result.pain_point || result.evidence_used || result.offer || result.why_now) ? (
              <details className="text-sm text-[var(--text-secondary)] group">
                <summary className="cursor-pointer text-cyan-400/90 hover:text-cyan-300 text-xs font-medium list-none flex items-center gap-2">
                  <span className="group-open:rotate-90 transition-transform inline-block">›</span> Supporting notes (not sent)
                </summary>
                <dl className="mt-3 space-y-2 pl-4 border-l border-[var(--border-subtle)]">
                  {result.pain_point ? (
                    <>
                      <dt className="text-[10px] uppercase tracking-wider">Pain point</dt>
                      <dd className="text-[var(--text-primary)]">{result.pain_point}</dd>
                    </>
                  ) : null}
                  {result.why_now ? (
                    <>
                      <dt className="text-[10px] uppercase tracking-wider mt-2">Why now</dt>
                      <dd className="text-[var(--text-primary)]">{result.why_now}</dd>
                    </>
                  ) : null}
                  {result.evidence_used ? (
                    <>
                      <dt className="text-[10px] uppercase tracking-wider mt-2">Evidence</dt>
                      <dd className="text-[var(--text-primary)]">{result.evidence_used}</dd>
                    </>
                  ) : null}
                  {result.offer ? (
                    <>
                      <dt className="text-[10px] uppercase tracking-wider mt-2">Offer angle</dt>
                      <dd className="text-[var(--text-primary)]">{result.offer}</dd>
                    </>
                  ) : null}
                </dl>
              </details>
            ) : null}

            {result.generated_alternatives_json?.trim() ? (
              <details className="text-xs">
                <summary className="cursor-pointer text-cyan-400/90 hover:text-cyan-300 font-medium list-none">
                  Extra variants (JSON)
                </summary>
                <pre className="mt-2 p-3 rounded-lg bg-black/30 border border-[var(--border-subtle)] overflow-x-auto max-h-48 overflow-y-auto whitespace-pre-wrap font-mono">
                  {result.generated_alternatives_json}
                </pre>
              </details>
            ) : null}
          </div>
        )}
      </div>
    </div>
  );
}
