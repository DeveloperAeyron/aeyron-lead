import { ReactNode } from "react";

interface ComingSoonProps {
  title: string;
  description: string;
  icon: ReactNode;
}

export default function ComingSoon({ title, description, icon }: ComingSoonProps) {
  return (
    <div className="relative min-h-screen bg-[var(--bg-primary)] p-8 flex items-center justify-center">
      <div className="glass-card rounded-3xl p-12 max-w-lg w-full text-center relative overflow-hidden">
        {/* Decorative background glow */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 w-64 h-64 bg-cyan-500/10 rounded-full blur-[80px] pointer-events-none" />
        
        <div className="relative z-10 flex flex-col items-center gap-6">
          <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-cyan-500/10 to-teal-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400 shadow-[0_0_30px_rgba(34,211,238,0.1)]">
            {icon}
          </div>
          
          <div className="space-y-2">
            <h1 className="text-3xl font-bold tracking-tight text-[var(--text-primary)]">
              {title}
            </h1>
            <p className="text-[var(--text-secondary)]">
              {description}
            </p>
          </div>

          <div className="mt-4 px-4 py-2 rounded-full border border-[var(--border-subtle)] bg-white/[0.02]">
            <span className="text-xs font-medium uppercase tracking-widest text-cyan-400">
              Still in development
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
