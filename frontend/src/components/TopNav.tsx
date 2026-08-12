import { NavLink } from "react-router-dom";
import { useAuthStore } from "../store/uiStore";

const TABS = [
  { to: "/inspection", label: "Inspection" },
  { to: "/registry", label: "Defect Registry" },
  { to: "/cognitive", label: "Cognitive Pipeline" },
  { to: "/compliance", label: "Compliance & Export" },
  { to: "/performance", label: "System Performance" },
];

export function TopNav() {
  const { name, role, logout } = useAuthStore();
  return (
    <header className="h-14 shrink-0 bg-bg-secondary border-b border-border flex items-center px-4 justify-between">
      <nav className="flex items-center gap-1">
        {TABS.map((t) => (
          <NavLink
            key={t.to}
            to={t.to}
            className={({ isActive }) =>
              `px-3 py-2 font-mono text-xs uppercase tracking-[0.1em] border-b-2 transition-colors ${
                isActive ? "border-accent-cyan text-accent-cyan" : "border-transparent text-text-secondary hover:text-text-primary"
              }`
            }
          >
            {t.label}
          </NavLink>
        ))}
      </nav>
      <div className="flex items-center gap-3 font-mono text-xs text-text-secondary">
        <span className="uppercase">
          {name} <span className="text-text-muted">({role})</span>
        </span>
        <button className="visi-btn" onClick={logout} type="button">
          Sign Out
        </button>
      </div>
    </header>
  );
}
