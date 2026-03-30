import PaperCard from "./PaperCard";
import DownloadedPapersPanel from "./DownloadedPapersPanel";
import { FileDown, Tag, BookOpen, CheckCircle2, AlertCircle, XCircle } from "lucide-react";
import clsx from "clsx";

const PDF_TIERS = [
  { key: "confirmed",  label: "Confirmed Report", sub: "≥70 score", icon: CheckCircle2, cls: "bg-green-900/20 border-green-700/40 text-green-300" },
  { key: "suspicious", label: "Suspicious Report", sub: "40-69 score", icon: AlertCircle, cls: "bg-yellow-900/20 border-yellow-700/40 text-yellow-300" },
  { key: "rejected",   label: "Rejected Report",  sub: "<40 score",  icon: XCircle, cls: "bg-red-900/20 border-red-700/40 text-red-300" },
];

function SummaryPDFs({ reports, apiBase }) {
  if (!reports) return null;
  const any = Object.values(reports).some(Boolean);
  if (!any) return null;

  const download = (filename) => {
    const key = localStorage.getItem("rpf_api_key") || "";
    fetch(`${apiBase}/search/pdf/${encodeURIComponent(filename)}`, { headers: { "X-API-Key": key } })
      .then((r) => r.blob())
      .then((blob) => {
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = filename;
        a.click();
      });
  };

  return (
    <div className="card border-brand/15 mb-3">
      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Tier Summary Reports (generated)</p>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
        {PDF_TIERS.map(({ key, label, sub, icon: Icon, cls }) => {
          const fn = reports[key];
          if (!fn) return null;
          return (
            <button key={key} onClick={() => download(fn)}
              className={clsx("flex items-center gap-2 px-3 py-2.5 rounded-lg border text-left hover:opacity-80 transition-opacity", cls)}>
              <Icon className="w-4 h-4 flex-shrink-0" />
              <div>
                <p className="text-xs font-semibold">{label}</p>
                <p className="text-xs opacity-60">{sub}</p>
              </div>
              <FileDown className="w-3 h-3 ml-auto flex-shrink-0 opacity-50" />
            </button>
          );
        })}
      </div>
    </div>
  );
}

export default function ResultsGrid({ result }) {
  const apiBase = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

  return (
    <div className="w-full max-w-3xl mx-auto space-y-4 fade-in">
      {/* Stats row */}
      <div className="flex flex-wrap gap-2 text-sm">
        <span className="flex items-center gap-1.5 bg-green-900/20 border border-green-700/30 text-green-300 px-3 py-1 rounded-full text-xs">
          <CheckCircle2 className="w-3 h-3" /> {result.total_found} confirmed
        </span>
        <span className="flex items-center gap-1.5 bg-yellow-900/20 border border-yellow-700/30 text-yellow-300 px-3 py-1 rounded-full text-xs">
          <AlertCircle className="w-3 h-3" /> {result.total_suspicious || 0} suspicious
        </span>
        <span className="flex items-center gap-1.5 bg-red-900/20 border border-red-700/30 text-red-300 px-3 py-1 rounded-full text-xs">
          <XCircle className="w-3 h-3" /> {result.total_rejected || 0} rejected
        </span>
        <span className="flex items-center gap-1.5 text-gray-500 text-xs ml-1">
          <Tag className="w-3 h-3 text-brand-light" /> {result.generated_terms?.length} search terms
        </span>
      </div>

      {/* Search terms */}
      <div className="flex flex-wrap gap-1">
        {result.generated_terms?.map((t, i) => (
          <span key={i} className="text-xs bg-surface-card border border-surface-border text-gray-400 px-2 py-0.5 rounded-full">{t}</span>
        ))}
      </div>

      {/* Summary PDFs */}
      <SummaryPDFs reports={result.pdf_reports} apiBase={apiBase} />

      {/* Downloaded paper PDFs */}
      <DownloadedPapersPanel downloaded={result.downloaded_papers} />

      {/* Confirmed papers list */}
      <div className="space-y-3">
        {result.papers?.map((paper, i) => (
          <PaperCard key={paper.id || i} paper={paper} rank={i + 1} />
        ))}
      </div>

      {result.papers?.length === 0 && (
        <div className="card text-center py-12 text-gray-500">
          <BookOpen className="w-10 h-10 mx-auto mb-3 opacity-30" />
          <p>No confirmed papers (score ≥ 70).</p>
          <p className="text-sm mt-1">Check the Suspicious Report PDF for possible matches.</p>
        </div>
      )}
    </div>
  );
}
