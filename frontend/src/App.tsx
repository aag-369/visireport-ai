import { Navigate, Route, Routes } from "react-router-dom";
import { TopNav } from "./components/TopNav";
import { Sidebar } from "./components/Sidebar";
import { LoginPage } from "./pages/LoginPage";
import { InspectionPage } from "./pages/InspectionPage";
import { DefectRegistryPage } from "./pages/DefectRegistryPage";
import { CognitivePipelinePage } from "./pages/CognitivePipelinePage";
import { ComplianceExportPage } from "./pages/ComplianceExportPage";
import { SystemPerformancePage } from "./pages/SystemPerformancePage";
import { useAuthStore } from "./store/uiStore";

function RequireAuth({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.token);
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="h-screen flex bg-bg-primary">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <TopNav />
        <main className="flex-1 overflow-y-auto">{children}</main>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/*"
        element={
          <RequireAuth>
            <Shell>
              <Routes>
                <Route path="/" element={<Navigate to="/inspection" replace />} />
                <Route path="/inspection" element={<InspectionPage />} />
                <Route path="/registry" element={<DefectRegistryPage />} />
                <Route path="/cognitive" element={<CognitivePipelinePage />} />
                <Route path="/compliance" element={<ComplianceExportPage />} />
                <Route path="/performance" element={<SystemPerformancePage />} />
              </Routes>
            </Shell>
          </RequireAuth>
        }
      />
    </Routes>
  );
}
