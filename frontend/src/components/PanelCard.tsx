import type { ReactNode } from "react";

export function PanelCard({
  title,
  children,
  className = "",
  actions,
}: {
  title: string;
  children: ReactNode;
  className?: string;
  actions?: ReactNode;
}) {
  return (
    <div className={`visi-panel flex flex-col ${className}`}>
      <div className="visi-panel-header justify-between">
        <span>{title}</span>
        {actions}
      </div>
      <div className="p-3 flex-1 min-h-0">{children}</div>
    </div>
  );
}
