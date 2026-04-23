"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import ThemeToggle from "./ThemeToggle";

export default function Sidebar() {
  const pathname = usePathname();
  const [isCollapsed, setIsCollapsed] = useState(false);

  const navItems = [
    {
      name: "Lead Hunt",
      href: "/leadhunt",
      icon: (
        <svg className="w-5 h-5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
      ),
    },
    {
      name: "History",
      href: "/dashboard",
      icon: (
        <svg className="w-5 h-5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
        </svg>
      ),
    },
    {
      name: "Lead Enrichment",
      href: "/enrichment",
      icon: (
        <svg className="w-5 h-5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5m.75-9l3-3 2.148 2.148A12.061 12.061 0 0116.5 7.605" />
        </svg>
      ),
    },
    {
      name: "Brand Reputation",
      href: "/reviews",
      icon: (
        <svg className="w-5 h-5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11.48 3.499a.562.562 0 011.04 0l2.125 5.111a.563.563 0 00.475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602a.563.563 0 00-.182.557l1.285 5.385a.562.562 0 01-.84.61l-4.725-2.885a.563.563 0 00-.586 0L6.982 20.54a.562.562 0 01-.84-.61l1.285-5.386a.562.562 0 00-.182-.557l-4.204-3.602a.563.563 0 01.321-.988l5.518-.442a.563.563 0 00.475-.345L11.48 3.5z" />
        </svg>
      ),
    },
    {
      name: "Site Generator",
      href: "/site-gen",
      icon: (
        <svg className="w-5 h-5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.25 6.75L22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3l-4.5 16.5" />
        </svg>
      ),
    },
    {
      name: "Campaign Builder",
      href: "/outreach",
      icon: (
        <svg className="w-5 h-5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25m19.5 0v.243a2.25 2.25 0 01-1.07 1.916l-7.5 4.615a2.25 2.25 0 01-2.36 0L3.32 8.91a2.25 2.25 0 01-1.07-1.916V6.75" />
        </svg>
      ),
    },
  ];

  return (
    <aside
      className={`border-r border-[var(--border-subtle)] bg-[var(--bg-primary)] flex flex-col h-screen sticky top-0 transition-all duration-300 z-50 ${
        isCollapsed ? "w-20" : "w-64"
      }`}
    >
      <div className={`p-6 flex items-center ${isCollapsed ? "justify-center" : "justify-between"}`}>
        <div className={`flex items-center gap-3 overflow-hidden ${isCollapsed ? "w-8" : "w-auto"}`}>
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-500 to-teal-600 flex flex-shrink-0 items-center justify-center shadow-lg shadow-cyan-500/20">
            <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 3.75H6A2.25 2.25 0 003.75 6v1.5M16.5 3.75H18A2.25 2.25 0 0120.25 6v1.5m0 9V18A2.25 2.25 0 0118 20.25h-1.5m-9 0H6A2.25 2.25 0 013.75 18v-1.5M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </div>
          {!isCollapsed && (
            <span className="font-bold text-lg tracking-tight text-[var(--text-primary)] whitespace-nowrap">
              Lead Radar
            </span>
          )}
        </div>
        {!isCollapsed && (
          <button
            onClick={() => setIsCollapsed(true)}
            className="p-1.5 rounded-lg hover:bg-white/5 text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
            title="Collapse Sidebar"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M18.75 19.5l-7.5-7.5 7.5-7.5m-6 15L5.25 12l7.5-7.5" />
            </svg>
          </button>
        )}
      </div>

      {isCollapsed && (
        <div className="flex justify-center pb-4">
          <button
            onClick={() => setIsCollapsed(false)}
            className="p-1.5 rounded-lg hover:bg-white/5 text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
            title="Expand Sidebar"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M11.25 4.5l7.5 7.5-7.5 7.5m-6-15l7.5 7.5-7.5 7.5" />
            </svg>
          </button>
        </div>
      )}

      <nav className={`flex-1 space-y-6 overflow-y-auto overflow-x-hidden scrollbar-thin ${isCollapsed ? "px-3" : "px-4"}`}>
        <div>
          {!isCollapsed && (
            <p className="px-4 text-[10px] font-semibold text-[var(--text-secondary)] uppercase tracking-widest mb-2">
              Core Tools
            </p>
          )}
          <div className="space-y-1">
            {navItems.slice(0, 2).map((item) => {
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  title={isCollapsed ? item.name : undefined}
                  className={`flex items-center gap-3 py-2.5 rounded-xl transition-all duration-200 group ${
                    isCollapsed ? "justify-center px-0" : "px-4"
                  } ${
                    isActive
                      ? "bg-cyan-500/10 text-cyan-400 border border-cyan-500/20"
                      : "text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-white/5 border border-transparent"
                  }`}
                >
                  <div className={`${isActive ? "text-cyan-400" : "text-[var(--text-secondary)] group-hover:text-[var(--text-primary)]"}`}>
                    {item.icon}
                  </div>
                  {!isCollapsed && <span className="font-medium text-sm whitespace-nowrap">{item.name}</span>}
                  {isActive && !isCollapsed && (
                    <div className="ml-auto flex-shrink-0 w-1.5 h-1.5 rounded-full bg-cyan-400 shadow-[0_0_8px_rgba(34,211,238,0.6)]" />
                  )}
                </Link>
              );
            })}
          </div>
        </div>

        <div>
          {!isCollapsed && (
            <p className="px-4 text-[10px] font-semibold text-[var(--text-secondary)] uppercase tracking-widest mb-2">
              Advanced (Beta)
            </p>
          )}
          {isCollapsed && <div className="h-px bg-white/5 mx-2 my-4" />}
          <div className="space-y-1">
            {navItems.slice(2).map((item) => {
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  title={isCollapsed ? item.name : undefined}
                  className={`flex items-center gap-3 py-2.5 rounded-xl transition-all duration-200 group ${
                    isCollapsed ? "justify-center px-0" : "px-4"
                  } ${
                    isActive
                      ? "bg-cyan-500/10 text-cyan-400 border border-cyan-500/20"
                      : "text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-white/5 border border-transparent"
                  }`}
                >
                  <div className={`${isActive ? "text-cyan-400" : "text-[var(--text-secondary)] group-hover:text-[var(--text-primary)]"}`}>
                    {item.icon}
                  </div>
                  {!isCollapsed && <span className="font-medium text-sm whitespace-nowrap">{item.name}</span>}
                  {isActive && !isCollapsed && (
                    <div className="ml-auto flex-shrink-0 w-1.5 h-1.5 rounded-full bg-cyan-400 shadow-[0_0_8px_rgba(34,211,238,0.6)]" />
                  )}
                </Link>
              );
            })}
          </div>
        </div>
      </nav>

      <div className={`p-4 mt-auto transition-all duration-300 ${isCollapsed ? "px-2" : "px-4"}`}>
        <div className={`glass-card rounded-xl border border-[var(--border-subtle)] ${isCollapsed ? "p-2 flex flex-col items-center gap-4" : "p-4"}`}>
          {!isCollapsed && (
            <p className="text-[10px] font-semibold text-[var(--text-secondary)] uppercase tracking-widest mb-2">
              System Status
            </p>
          )}
          <div className={`flex ${isCollapsed ? "flex-col gap-4" : "items-center justify-between"}`}>
            {!isCollapsed && (
              <span className="text-xs text-[var(--text-secondary)] font-mono">v1.0.4</span>
            )}
            
            <ThemeToggle />

            <div className="flex flex-col items-center">
              <div className="flex items-center gap-1.5" title={isCollapsed ? "System Online" : undefined}>
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                {!isCollapsed && (
                  <span className="text-[10px] text-emerald-500/80 font-medium uppercase tracking-tighter">Live</span>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}
