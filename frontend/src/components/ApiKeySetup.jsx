import { useState } from "react";
import { Eye, EyeOff, Shield } from "lucide-react";
import { createApiKey, api } from "../api/client";

export default function ApiKeySetup({ onReady }) {
  const [accessToken, setAccessToken] = useState("");
  const [show, setShow] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // Verify token → auto-create API key → done (no separate API key step)
  const handleToken = async (e) => {
    e.preventDefault();
    const t = accessToken.trim();
    if (!t) return;
    setLoading(true);
    setError("");
    try {
      // 1. Verify access token
      await api.get("/health", { headers: { "X-Access-Token": t } });
      localStorage.setItem("rpf_access_token", t);

      // 2. Auto-create an API key (no user action needed)
      const res = await createApiKey("default");
      localStorage.setItem("rpf_api_key", res.key);
      onReady(res.key);
    } catch (err) {
      localStorage.removeItem("rpf_access_token");
      if (err.response?.status === 401) {
        setError("Access token rejected. Check the token printed by expose.sh.");
      } else {
        setError(err.response?.data?.detail || "Could not connect to server.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="card w-full max-w-md space-y-6">
        <div className="text-center">
          <div className="w-14 h-14 bg-brand/10 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <Shield className="w-7 h-7 text-brand-light" />
          </div>
          <h1 className="text-xl font-bold text-white">Research Paper Finder</h1>
          <p className="text-gray-400 text-sm mt-1">Enter server access token</p>
          <p className="text-gray-600 text-xs mt-1">
            Run <code className="bg-surface-border px-1 rounded">./scripts/expose.sh</code> on your VPS to get the token
          </p>
        </div>
        <form onSubmit={handleToken} className="space-y-3">
          <div className="relative">
            <input
              type={show ? "text" : "password"}
              value={accessToken}
              onChange={(e) => setAccessToken(e.target.value)}
              placeholder="Paste access token from server..."
              className="w-full bg-surface border border-surface-border rounded-lg px-4 py-3 pr-10 text-sm focus:outline-none focus:border-brand"
            />
            <button
              type="button"
              onClick={() => setShow(!show)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500"
            >
              {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
          {error && <p className="text-red-400 text-xs">{error}</p>}
          <button
            type="submit"
            className="btn-primary w-full flex items-center justify-center gap-2"
            disabled={!accessToken.trim() || loading}
          >
            {loading ? <div className="spinner" /> : null}
            {loading ? "Connecting..." : "Connect"}
          </button>
        </form>
      </div>
    </div>
  );
}
