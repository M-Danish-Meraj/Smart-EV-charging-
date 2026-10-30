import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/format";

export function Button({
  icon: Icon,
  children,
  variant = "outline",
  className,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  icon?: LucideIcon;
  variant?: "outline" | "solid" | "ghost";
}) {
  return (
    <button
      {...props}
      className={cn(
        "inline-flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors focus-visible:outline-2 focus-visible:outline-cyan-neon",
        variant === "solid" && "bg-cyan-neon text-slate-950 hover:bg-cyan-300",
        variant === "outline" && "border border-slate-700 text-slate-200 hover:border-cyan-neon/60 hover:text-cyan-neon",
        variant === "ghost" && "text-slate-400 hover:text-slate-100",
        className,
      )}
    >
      {Icon && <Icon className="h-3.5 w-3.5" aria-hidden />}
      {children}
    </button>
  );
}
