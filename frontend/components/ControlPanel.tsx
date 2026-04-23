"use client";

import { useState } from "react";
import { ScrapeConfig, DEFAULT_CONFIG } from "@/lib/types";

interface ControlPanelProps {
  onStart: (config: ScrapeConfig) => void;
  onStop: () => void;
  isRunning: boolean;
}

export default function ControlPanel({ onStart, onStop, isRunning }: ControlPanelProps) {
  const [config, setConfig] = useState<ScrapeConfig>({ ...DEFAULT_CONFIG });
  const [showAdvanced, setShowAdvanced] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onStart(config);
  };

  const update = <K extends keyof ScrapeConfig>(key: K, value: ScrapeConfig[K]) => {
    setConfig((prev) => ({ ...prev, [key]: value }));
  };

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <div className="glass-card rounded-2xl p-6 space-y-5">
        {/* Header */}
        <div className="flex items-center gap-3 mb-1">
          <div className="h-8 w-1 rounded-full bg-gradient-to-b from-cyan-400 to-teal-500" />
          <h2 className="text-lg font-semibold text-[var(--text-primary)] tracking-tight">
            Search Configuration
          </h2>
        </div>

        {/* Primary inputs */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="space-y-1.5">
            <label htmlFor="query" className="text-xs font-medium text-[var(--text-secondary)] uppercase tracking-wider">
              Query
            </label>
            <input
              id="query"
              type="text"
              value={config.query}
              onChange={(e) => update("query", e.target.value)}
              placeholder="e.g. car wash"
              className="input-field"
              required
            />
          </div>
          <div className="space-y-1.5">
            <label htmlFor="location" className="text-xs font-medium text-[var(--text-secondary)] uppercase tracking-wider">
              Location
            </label>
            <input
              id="location"
              type="text"
              value={config.location}
              onChange={(e) => update("location", e.target.value)}
              placeholder="e.g. Delaware"
              className="input-field"
              required
            />
          </div>
          <div className="space-y-1.5">
            <label htmlFor="limit" className="text-xs font-medium text-[var(--text-secondary)] uppercase tracking-wider">
              Max Leads
            </label>
            <input
              id="limit"
              type="number"
              value={config.limit}
              onChange={(e) => update("limit", parseInt(e.target.value) || 50)}
              min={1}
              max={1000}
              className="input-field"
            />
          </div>
        </div>

        {/* Advanced settings panel */}
        <div
          className={`grid grid-cols-2 md:grid-cols-4 gap-4 overflow-hidden transition-all duration-300 ${
            showAdvanced ? "max-h-96 opacity-100 mt-2 mb-4" : "max-h-0 opacity-0"
          }`}
        >
          <div className="space-y-1.5">
            <label htmlFor="radius_km" className="text-xs font-medium text-[var(--text-secondary)] uppercase tracking-wider">
              Radius (km)
            </label>
            <input
              id="radius_km"
              type="number"
              step="0.1"
              value={config.radius_km}
              onChange={(e) => update("radius_km", parseFloat(e.target.value) || 1.0)}
              className="input-field"
            />
          </div>
          <div className="space-y-1.5">
            <label htmlFor="max_depth" className="text-xs font-medium text-[var(--text-secondary)] uppercase tracking-wider">
              Max Depth
            </label>
            <input
              id="max_depth"
              type="number"
              value={config.max_depth}
              onChange={(e) => update("max_depth", parseInt(e.target.value) || 3)}
              className="input-field"
            />
          </div>
          <div className="space-y-1.5">
            <label htmlFor="root_count" className="text-xs font-medium text-[var(--text-secondary)] uppercase tracking-wider">
              Root Count
            </label>
            <input
              id="root_count"
              type="number"
              value={config.root_count}
              onChange={(e) => update("root_count", parseInt(e.target.value) || 50)}
              className="input-field"
            />
          </div>
          <div className="space-y-1.5">
            <label htmlFor="zoom" className="text-xs font-medium text-[var(--text-secondary)] uppercase tracking-wider">
              Zoom Level
            </label>
            <input
              id="zoom"
              type="number"
              value={config.zoom}
              onChange={(e) => update("zoom", parseInt(e.target.value) || 15)}
              className="input-field"
            />
          </div>
        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-between pt-5 border-t border-white/5">
          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="flex items-center gap-2 text-sm text-[var(--text-secondary)] hover:text-cyan-400 transition-colors group"
          >
            <svg
              className={`w-4 h-4 transition-transform duration-200 ${showAdvanced ? "rotate-90 text-cyan-400" : ""}`}
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={2}
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
            </svg>
            <span>Advanced Settings</span>
          </button>

          <div className="flex gap-3">
            {!isRunning ? (
              <button
                type="submit"
                id="start-scrape-btn"
                className="btn-primary !px-8 !py-2.5 text-sm"
              >
                <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
                </svg>
                Start Scraping
              </button>
            ) : (
              <button
                type="button"
                onClick={onStop}
                id="stop-scrape-btn"
                className="btn-danger !px-8 !py-2.5 text-sm"
              >
                <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5.25 7.5A2.25 2.25 0 017.5 5.25h9a2.25 2.25 0 012.25 2.25v9a2.25 2.25 0 01-2.25 2.25h-9a2.25 2.25 0 01-2.25-2.25v-9z" />
                </svg>
                Stop Scraping
              </button>
            )}
          </div>
        </div>
      </div>
    </form>
  );
}
