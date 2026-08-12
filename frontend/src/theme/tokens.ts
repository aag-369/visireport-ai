// Single source of truth for the Section 5.1 theme tokens - used anywhere
// JS needs a raw hex value (charts, canvas overlays) rather than a
// Tailwind class name.
export const colors = {
  bgPrimary: "#0A0C0F",
  bgSecondary: "#111418",
  bgTertiary: "#1A1F26",
  bgTerminal: "#050709",
  border: "#252C36",
  accentCyan: "#00D4FF",
  accentAmber: "#FFB020",
  accentCrimson: "#FF3B3B",
  accentGreen: "#00E676",
  accentPurple: "#9B6DFF",
  textPrimary: "#E8EDF5",
  textSecondary: "#8896A8",
  textMuted: "#4A5568",
  termGreen: "#00FF88",
} as const;

export type DefectClass = "open" | "short" | "mousebite" | "spur" | "copper" | "pin-hole";

export const defectColors: Record<DefectClass, string> = {
  open: "#2979FF",
  short: "#FF3B3B",
  mousebite: "#FF6EC7",
  spur: "#FFB020",
  copper: "#FF6D00",
  "pin-hole": "#00E676",
};

export const defectDisplayNames: Record<DefectClass, string> = {
  open: "Open Circuit",
  short: "Short Circuit",
  mousebite: "Mousebite",
  spur: "Spur",
  copper: "Spurious Copper",
  "pin-hole": "Pin-hole",
};

export type Severity = "CRITICAL" | "MAJOR" | "MINOR";

export const severityColors: Record<Severity, string> = {
  CRITICAL: "#FF3B3B",
  MAJOR: "#FFB020",
  MINOR: "#00E676",
};
