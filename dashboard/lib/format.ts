// Number formatting with explicit units. SI prefixes (1 KB = 1000 bytes).

export function fmtMs(ms: number): string {
  if (ms < 1) return `${ms.toFixed(3)} ms`;
  if (ms < 100) return `${ms.toFixed(2)} ms`;
  return `${Math.round(ms).toLocaleString("en-US")} ms`;
}

export function fmtBytes(bytes: number): string {
  if (bytes < 1_000) return `${bytes} B`;
  if (bytes < 1_000_000) return `${(bytes / 1_000).toFixed(1)} KB`;
  return `${(bytes / 1_000_000).toFixed(1)} MB`;
}

export const fmtInt = (n: number) => n.toLocaleString("en-US");

export const pct = (part: number, whole: number) =>
  whole === 0 ? "n/a" : `${((100 * part) / whole).toFixed(0)}%`;

export function cn(...classes: (string | false | null | undefined)[]): string {
  return classes.filter(Boolean).join(" ");
}

// Identity colours for stations; status colours are kept separate.
export const STATION_COLOR: Record<string, string> = {
  ST1: "#00F0FF",
  ST2: "#A78BFA",
  ST3: "#F472B6",
  ST4: "#60A5FA",
};

export const COLOR = {
  cyan: "#00F0FF",
  emerald: "#10B981",
  red: "#EF4444",
  amber: "#F59E0B",
  slate: "#64748B",
  grid: "#1E293B",
  ink: "#E2E8F0",
  muted: "#94A3B8",
};
