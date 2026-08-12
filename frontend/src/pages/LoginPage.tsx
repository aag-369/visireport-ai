import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, tokenStorage } from "../api/client";
import { useAuthStore } from "../store/uiStore";

export function LoginPage() {
  const [email, setEmail] = useState("engineer@visireport.ai");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const setAuth = useAuthStore((s) => s.setAuth);
  const navigate = useNavigate();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await api.login(email, password);
      tokenStorage.set("visireport_token", res.access_token);
      setAuth(res.access_token, res.name, res.role);
      navigate("/inspection");
    } catch {
      setError("Invalid credentials. Check the seed engineer email/password in your .env.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg-primary">
      <form onSubmit={handleSubmit} className="visi-panel w-96">
        <div className="visi-panel-header">VisiReport AI · Sign In</div>
        <div className="p-5 flex flex-col gap-4">
          <span className="visi-iso-badge self-start">ISO 13485:2016 Cl. 8.3 &amp; 8.5.2</span>
          <label className="flex flex-col gap-1 text-xs font-mono uppercase text-text-secondary">
            Email
            <input className="visi-input" value={email} onChange={(e) => setEmail(e.target.value)} type="email" required />
          </label>
          <label className="flex flex-col gap-1 text-xs font-mono uppercase text-text-secondary">
            Password
            <input className="visi-input" value={password} onChange={(e) => setPassword(e.target.value)} type="password" required />
          </label>
          {error && <div className="text-accent-crimson text-xs font-mono">{error}</div>}
          <button className="visi-btn visi-btn-primary" type="submit" disabled={loading}>
            {loading ? "Authenticating..." : "Sign In"}
          </button>
        </div>
      </form>
    </div>
  );
}
