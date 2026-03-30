import { useEffect, useState } from "react";
import { Shield } from "lucide-react";
import { createApiKey } from "../api/client";

export default function ApiKeySetup({ onReady }) {
  const [status, setStatus] = useState("Initializing...");
  const [error, setError] = useState("");

  useEffect(() => {
    const autoSetup = async () => {
      try {
        setStatus("Creating API key...");
        // Auto-create an API key with a unique name
        const res = await createApiKey(`session-${Date.now()}`);
        localStorage.setItem("rpf_api_key", res.key);
        onReady(res.key);
      } catch (err) {
        console.error("Setup error:", err);
        setError(err.response?.data?.detail || "Could not connect to server. Check your internet connection.");
      }
    };

    autoSetup();
  }, [onReady]);

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="card w-full max-w-md space-y-6">
        <div className="text-center">
          <div className="w-14 h-14 bg-brand/10 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <Shield className="w-7 h-7 text-brand-light" />
          </div>
          <h1 className="text-xl font-bold text-white">Research Paper Finder</h1>
          <p className="text-gray-400 text-sm mt-4">{status}</p>
          {error && (
            <div className="mt-4 p-3 bg-red-900/20 border border-red-800/50 rounded-lg">
              <p className="text-red-400 text-xs">{error}</p>
              <button
                onClick={() => window.location.reload()}
                className="mt-3 text-red-300 hover:text-red-200 text-xs underline"
              >
                Retry
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
