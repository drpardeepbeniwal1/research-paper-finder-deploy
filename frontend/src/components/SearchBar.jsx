import { useState } from "react";
import { Search, Loader2, Settings2 } from "lucide-react";
import clsx from "clsx";

export default function SearchBar({ onSearch, loading }) {
  const [query, setQuery] = useState("");
  const [showFilters, setShowFilters] = useState(false);
  const [yearFrom, setYearFrom] = useState("");
  const [yearTo, setYearTo] = useState("");
  const [maxResults, setMaxResults] = useState(50);
  const [includeAssociated, setIncludeAssociated] = useState(false);
  const [email, setEmail] = useState("");

  const submit = (e) => {
    e.preventDefault();
    if (!query.trim() || loading) return;
    onSearch({
      query: query.trim(),
      year_from: yearFrom ? parseInt(yearFrom) : null,
      year_to: yearTo ? parseInt(yearTo) : null,
      max_results: maxResults,
      include_associated: includeAssociated,
      email: email.trim() || null,
    });
  };

  return (
    <form onSubmit={submit} className="w-full max-w-3xl mx-auto space-y-3">
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 w-5 h-5" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g. transformer attention for long sequences, CRISPR gene editing 2023..."
            className="w-full bg-surface-card border border-surface-border rounded-xl pl-11 pr-4 py-3.5 text-white placeholder-gray-500 focus:outline-none focus:border-brand transition-colors"
          />
        </div>
        <button type="submit" className="btn-primary flex items-center gap-2 min-w-[110px] justify-center" disabled={loading || !query.trim()}>
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
          {loading ? "Searching" : "Search"}
        </button>
        <button type="button" onClick={() => setShowFilters(!showFilters)}
          className={clsx("btn-outline flex items-center gap-1.5", showFilters && "border-brand text-white")}>
          <Settings2 className="w-4 h-4" /> Filters
        </button>
      </div>

      {showFilters && (
        <div className="card fade-in grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Year From</label>
            <input type="number" value={yearFrom} onChange={(e) => setYearFrom(e.target.value)}
              placeholder="2010" min="1900" max="2100"
              className="w-full bg-surface border border-surface-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-brand" />
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Year To</label>
            <input type="number" value={yearTo} onChange={(e) => setYearTo(e.target.value)}
              placeholder="2025" min="1900" max="2100"
              className="w-full bg-surface border border-surface-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-brand" />
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Max Results</label>
            <select value={maxResults} onChange={(e) => setMaxResults(parseInt(e.target.value))}
              className="w-full bg-surface border border-surface-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-brand">
              {[1, 5, 10, 50, 100, 200, 500, 1000].map(n => <option key={n} value={n}>{n}</option>)}
              <option value={9999}>Unlimited</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Notify Email (optional)</label>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              className="w-full bg-surface border border-surface-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-brand" />
          </div>
        </div>
      )}
    </form>
  );
}
