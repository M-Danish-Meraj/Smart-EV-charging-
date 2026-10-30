import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/format";

export function Card({
  title,
  subtitle,
  icon: Icon,
  action,
  className,
  children,
}: {
  title?: string;
  subtitle?: string;
  icon?: LucideIcon;
  action?: React.ReactNode;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div className={cn("glass p-4 sm:p-5", className)}>
      {(title || action) && (
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            {title && (
              <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-100">
                {Icon && <Icon className="h-4 w-4 text-cyan-neon" aria-hidden />}
                {title}
              </h3>
            )}
            {subtitle && <p className="mt-1 text-xs text-slate-400">{subtitle}</p>}
          </div>
          {action}
        </div>
      )}
      {children}
    </div>
  );
}

export function Stat({ label, value, tone }: { label: string; value: React.ReactNode; tone?: string }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-950/50 px-3 py-2">
      <div className="text-[11px] uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-0.5 font-mono text-sm font-semibold" style={{ color: tone ?? "#e2e8f0" }}>
        {value}
      </div>
    </div>
  );
}
