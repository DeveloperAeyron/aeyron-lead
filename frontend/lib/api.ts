const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const api = {
  scrapeUrl: `${API_BASE}/api/scrape`,
  stopUrl: `${API_BASE}/api/stop`,
  exportUrl: (sessionId: string) => `${API_BASE}/api/export/${sessionId}`,
  sessionLeadsUrl: (sessionId: string) => `${API_BASE}/api/sessions/${sessionId}/leads`,
  enrichUrl: `${API_BASE}/api/enrich-website`,
  healthUrl: `${API_BASE}/api/health`,
};
