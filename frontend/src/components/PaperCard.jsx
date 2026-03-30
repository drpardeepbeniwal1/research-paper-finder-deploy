import { useState } from "react";
import { ExternalLink, FileText, ChevronDown, ChevronUp, BookOpen } from "lucide-react";
import clsx from "clsx";

function ScoreBadge({ score }) {
  const cls = score >= 70 ? "score-high" : score >= 50 ? "score-mid" : "score-low";
  return <span className={cls}>{score.toFixed(0)}/100</span>;
}

function AssociatedPaper({ paper }) {
  return (
    <div className="bg-surface/60 border border-surface-border/50 rounded-lg p-3 text-sm">
      <div className="flex items-start justify-between gap-2">
        <p className="font-medium text-gray-200 leading-snug line-clamp-2">{paper.title}</p>
        <ScoreBadge score={paper.relevance_score || 0} />
      </div>
      <p className="text-gray-500 text-xs mt-1">{paper.source} · {paper.year || "?"}</p>
    </div>
  );
}

export default function PaperCard({ paper, rank }) {
  const [expanded, setExpanded] = useState(false);
  const [showAssoc, setShowAssoc] = useState(false);

  const authors = paper.authors?.slice(0, 3).join(", ") + (paper.authors?.length > 3 ? ` +${paper.authors.length - 3}` : "");

  return (
    <div className={clsx("card fade-in hover:border-brand/40 transition-all", rank <= 3 && "border-brand/20")}>
      <div className="flex items-start gap-3">
        {rank && (
          <div className={clsx("flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center text-sm font-bold",
            rank === 1 ? "bg-yellow-500/20 text-yellow-400" :
            rank === 2 ? "bg-gray-400/20 text-gray-300" :
            rank === 3 ? "bg-amber-600/20 text-amber-500" :
            "bg-surface-border/30 text-gray-500")}>
            {rank}
          </div>
        )}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-3">
            <h3 className="font-semibold text-white leading-snug">{paper.title}</h3>
            <ScoreBadge score={paper.relevance_score || 0} />
          </div>

          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-1.5 text-xs text-gray-400">
            {authors && <span>{authors}</span>}
            {paper.year && <span className="bg-surface-border/50 px-2 py-0.5 rounded">{paper.year}</span>}
            <span className="bg-brand/10 text-brand-light px-2 py-0.5 rounded">{paper.source}</span>
          </div>

          {paper.relevance_reasoning && (
            <p className="mt-2 text-xs text-gray-400 italic border-l-2 border-brand/30 pl-2">{paper.relevance_reasoning}</p>
          )}

          {paper.abstract && (
            <div className="mt-3">
              <p className={clsx("text-sm text-gray-300 leading-relaxed", !expanded && "line-clamp-3")}>
                {paper.abstract}
              </p>
              {paper.abstract.length > 200 && (
                <button onClick={() => setExpanded(!expanded)}
                  className="text-xs text-brand-light hover:text-brand mt-1 flex items-center gap-1">
                  {expanded ? <><ChevronUp className="w-3 h-3" /> Show less</> : <><ChevronDown className="w-3 h-3" /> Read more</>}
                </button>
              )}
            </div>
          )}

          <div className="flex flex-wrap gap-2 mt-3">
            {paper.url && (
              <a href={paper.url} target="_blank" rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-xs btn-outline py-1.5">
                <ExternalLink className="w-3 h-3" /> View Paper
              </a>
            )}
            {paper.pdf_url && (
              <a href={paper.pdf_url} target="_blank" rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-xs bg-brand/10 hover:bg-brand/20 text-brand-light border border-brand/30 px-3 py-1.5 rounded-lg transition-colors">
                <FileText className="w-3 h-3" /> PDF
              </a>
            )}
            {paper.associated_papers?.length > 0 && (
              <button onClick={() => setShowAssoc(!showAssoc)}
                className="inline-flex items-center gap-1.5 text-xs btn-outline py-1.5">
                <BookOpen className="w-3 h-3" />
                {showAssoc ? "Hide" : "Show"} Associated ({paper.associated_papers.length})
              </button>
            )}
          </div>

          {showAssoc && paper.associated_papers?.length > 0 && (
            <div className="mt-3 space-y-2 fade-in">
              <p className="text-xs text-gray-500 font-medium uppercase tracking-wider">Associated Papers</p>
              {paper.associated_papers.map((ap, i) => <AssociatedPaper key={i} paper={ap} />)}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
