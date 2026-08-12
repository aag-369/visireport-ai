import { defectColors, severityColors, type DefectClass, type Severity } from "../theme/tokens";

export function DefectBadge({ defectClass }: { defectClass: string }) {
  const color = defectColors[defectClass as DefectClass] ?? "#8896A8";
  return (
    <span
      className="visi-badge border"
      style={{ borderColor: color, color, backgroundColor: `${color}18` }}
    >
      {defectClass}
    </span>
  );
}

export function SeverityBadge({ severity }: { severity: string }) {
  const color = severityColors[severity as Severity] ?? "#8896A8";
  return (
    <span
      className="visi-badge border"
      style={{ borderColor: color, color, backgroundColor: `${color}18` }}
    >
      {severity}
    </span>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    PENDING: "#8896A8",
    CONFIRMED: "#00E676",
    OVERRIDDEN: "#9B6DFF",
  };
  const color = map[status] ?? "#8896A8";
  return (
    <span className="visi-badge border" style={{ borderColor: color, color, backgroundColor: `${color}18` }}>
      {status}
    </span>
  );
}
