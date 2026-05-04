const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/+$/, "");

/** ngrok free tier can show an interstitial; this header skips it for API calls. */
function isNgrokHost(): boolean {
  try {
    const host = new URL(API_BASE).hostname;
    return (
      host.endsWith(".ngrok-free.app") ||
      host.endsWith(".ngrok.app") ||
      host.includes(".ngrok.io")
    );
  } catch {
    return false;
  }
}

/** Merge into fetch options so all backend calls behave when NEXT_PUBLIC_API_URL is ngrok. */
export function withApiHeaders(init: RequestInit = {}): RequestInit {
  if (!isNgrokHost()) return init;
  const headers = new Headers(init.headers);
  headers.set("ngrok-skip-browser-warning", "true");
  return { ...init, headers };
}

export const api = {
  scrapeUrl: `${API_BASE}/api/scrape`,
  stopUrl: `${API_BASE}/api/stop`,
  exportUrl: (sessionId: string) => `${API_BASE}/api/export/${sessionId}`,
  sessionsUrl: `${API_BASE}/api/sessions`,
  sessionLeadsUrl: (sessionId: string) => `${API_BASE}/api/sessions/${sessionId}/leads`,
  enrichUrl: `${API_BASE}/api/enrich-website`,
  generateEmailUrl: `${API_BASE}/api/generate-email`,
  generateEmailBatchUrl: `${API_BASE}/api/generate-email/batch`,
  healthUrl: `${API_BASE}/api/health`,
};
