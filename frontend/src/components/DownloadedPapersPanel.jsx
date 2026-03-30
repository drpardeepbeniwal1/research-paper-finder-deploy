import { useState } from "react";
import { FolderOpen, FileText, ChevronDown, ChevronUp } from "lucide-react";
import clsx from "clsx";

const TIER_CONFIG = {
  accepted: { label: "Accepted", color: "text-green-400 border-green-700/40 bg-green-900/10", dot: "bg-green-400" },
  maybe:    { label: "Maybe",    color: "text-yellow-400 border-yellow-700/40 bg-yellow-900/10", dot: "bg-yellow-400" },
  rejected: { label: "Rejected", color: "text-red-400 border-red-700/40 bg-red-900/10", dot: "bg-red-400" },
};

function TierFolder({ tier, paths, apiBase }) {
  const [open, setOpen] = useState(tier === "accepted");
  const cfg = TIER_CONFIG[tier];
  if (!paths || paths.length === 0) return null;

  return (
    <div className={clsx("border rounded-lg overflow-hidden", cfg.color)}>
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-3 py-2.5 hover:opacity-80 transition-opacity"
      >
        <span className="flex items-center gap-2 text-sm font-medium">
          <span className={clsx("w-2 h-2 rounded-full flex-shrink-0", cfg.dot)} />
          <FolderOpen className="w-3.5 h-3.5" />
          {cfg.label} Papers
          <span className="text-xs opacity-60">({paths.length} downloaded)</span>
        </span>
        {open ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
      </button>

      {open && (
        <div className="border-t border-current/20 divide-y divide-current/10 max-h-48 overflow-y-auto">
          {paths.map((p, i) => {
            const filename = p.split("/").pop();
            const url = `${apiBase}/search/papers/${tier}/${encodeURIComponent(filename)}`;
            const key = localStorage.getItem("rpf_api_key") || "";
            return (
              <button
                key={i}
                onClick={() => {
                  fetch(url, { headers: { "X-API-Key": key } })
                    .then((r) => r.blob())
                    .then((blob) => {
                      const a = document.createElement("a");
                      a.href = URL.createObjectURL(blob);
                      a.download = filename;
                      a.click();
                    });
                }}
                className="w-full flex items-center gap-2 px-3 py-1.5 hover:opacity-70 text-left transition-opacity"
              >
                <FileText className="w-3 h-3 flex-shrink-0 opacity-60" />
                <span className="text-xs truncate">{filename.replace(/_/g, " ").replace(".pdf", "")}</span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default function DownloadedPapersPanel({ downloaded }) {
  const apiBase = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
  const total = Object.values(downloaded || {}).flat().length;
  if (total === 0) return null;

  return (
    <div className="card border-surface-border/80 mb-4">
      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3 flex items-center gap-2">
        <FolderOpen className="w-3.5 h-3.5 text-brand-light" />
        Downloaded Paper PDFs ({total} files)
        <span className="text-gray-600 normal-case font-normal">· stored in data/papers/</span>
      </p>
      <div className="space-y-2">
        {["accepted", "maybe", "rejected"].map((tier) => (
          <TierFolder
            key={tier}
            tier={tier}
            paths={downloaded?.[tier] || []}
            apiBase={apiBase}
          />
        ))}
      </div>
    </div>
  );
}
