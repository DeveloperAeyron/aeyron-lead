const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/+$/, "");

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
