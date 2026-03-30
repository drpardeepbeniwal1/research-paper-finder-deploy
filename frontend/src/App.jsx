import { useState, useEffect, useRef } from "react";
import { useMutation } from "@tanstack/react-query";
import { searchPapers, getSearchStatus } from "./api/client";
import SearchBar from "./components/SearchBar";
import ResultsGrid from "./components/ResultsGrid";
import ApiKeySetup from "./components/ApiKeySetup";
import { BookOpen, Cpu, LogOut, AlertCircle } from "lucide-react";

function Header({ onLogout }) {
  return (
    <header className="border-b border-surface-border bg-surface-card/50 sticky top-0 z-10 backdrop-blur-sm">
      <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 bg-brand/20 rounded-lg flex items-center justify-center">
            <BookOpen className="w-4 h-4 text-brand-light" />
          </div>
          <div>
            <h1 className="font-bold text-sm text-white">Research Paper Finder</h1>
            <p className="text-xs text-gray-500 flex items-center gap-1">
              <Cpu className="w-3 h-3" /> Powered by NVIDIA Nemotron-70B
            </p>
          </div>
        </div>
        <button onClick={onLogout} className="text-gray-500 hover:text-gray-300 transition-colors" title="Change API Key">
          <LogOut className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
}

export default function App() {
  const [apiKey, setApiKey] = useState(() => localStorage.getItem("rpf_api_key") || "");
  const [results, setResults] = useState(null);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState(null);
  const [progress, setProgress] = useState(null);
  const [progressPercent, setProgressPercent] = useState(0);
  const pollTimer = useRef(null);

  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const token = urlParams.get("token");
    if (token) {
      localStorage.setItem("rpf_access_token", token);
      urlParams.delete("token");
      const newSearch = urlParams.toString();
      const newUrl = window.location.pathname + (newSearch ? "?" + newSearch : "");
      window.history.replaceState({}, "", newUrl);
    }
    
    return () => {
      if (pollTimer.current) clearTimeout(pollTimer.current);
    };
  }, []);

  const startPolling = async (taskId) => {
    try {
      const data = await getSearchStatus(taskId);
      setProgress(data.progress || null);
      setProgressPercent(data.progress_percent || 0);

      if (data.status === "completed") {
        setResults(data.result);
        setIsSearching(false);
        setProgress("Search completed!");
        setProgressPercent(100);
      } else if (data.status === "failed") {
        setSearchError(data.error || "Search failed on server");
        setIsSearching(false);
      } else {
        pollTimer.current = setTimeout(() => startPolling(taskId), 1500);
      }
    } catch (err) {
      setSearchError(err.response?.data?.detail || err.message);
      setIsSearching(false);
    }
  };

  const searchMutation = useMutation({
    mutationFn: searchPapers,
    onSuccess: (data) => {
      setSearchError(null);
      setResults(null);
      setIsSearching(true);
      startPolling(data.task_id);
    },
    onError: (err) => {
      setSearchError(err.response?.data?.detail || err.message);
    }
  });

  const handleLogout = () => {
    if (pollTimer.current) clearTimeout(pollTimer.current);
    localStorage.removeItem("rpf_api_key");
    localStorage.removeItem("rpf_access_token");
    setApiKey("");
    setResults(null);
    setIsSearching(false);
  };

  if (!apiKey) return <ApiKeySetup onReady={setApiKey} />;

  return (
    <div className="min-h-screen flex flex-col">
      <Header onLogout={handleLogout} />

      <main className="flex-1 max-w-5xl mx-auto w-full px-4 py-8 space-y-8">
        {/* Hero */}
        {!results && !isSearching && !searchMutation.isPending && (
          <div className="text-center space-y-3 py-8 fade-in">
            <h2 className="text-3xl font-bold text-white">Deep Research Paper Discovery</h2>
            <p className="text-gray-400 max-w-xl mx-auto">
              AI-powered search across arXiv, Semantic Scholar, and OpenAlex.
              LLM analyzes and scores every paper for relevance.
            </p>
            <div className="flex justify-center gap-4 text-sm text-gray-500 mt-2">
              <span>✓ Year filtering</span>
              <span>✓ Associated papers</span>
              <span>✓ PDF summaries</span>
              <span>✓ Relevance scoring</span>
            </div>
          </div>
        )}

        {/* Search */}
        <div className="flex justify-center">
          <SearchBar onSearch={searchMutation.mutate} loading={isSearching || searchMutation.isPending} />
        </div>

        {/* Loading state with live activity */}
        {(isSearching || searchMutation.isPending) && (
          <div className="text-center space-y-4 py-12 fade-in">
            <div className="w-10 h-10 spinner mx-auto" style={{ width: 40, height: 40 }} />
            <div>
              <p className="text-white font-medium">Deep searching research papers...</p>
              <p className="text-gray-500 text-sm mt-1">
                {progress || "Generating search terms → Fetching papers → LLM scoring"}
              </p>
              {progressPercent > 0 && (
                <div className="mt-3 max-w-md mx-auto">
                  <div className="w-full h-2 bg-surface-border rounded-full overflow-hidden">
                    <div className="h-full bg-brand transition-all" style={{ width: `${progressPercent}%` }} />
                  </div>
                  <p className="text-xs text-gray-600 mt-1">{progressPercent}%</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Error */}
        {searchError && (
          <div className="max-w-3xl mx-auto card border-red-800/50 bg-red-900/10 flex items-start gap-3 fade-in">
            <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-red-300 font-medium">Search failed</p>
              <p className="text-red-400/80 text-sm mt-0.5">{searchError}</p>
            </div>
          </div>
        )}

        {/* Results */}
        {results && !isSearching && (
          <div className="flex justify-center">
            <ResultsGrid result={results} />
          </div>
        )}
      </main>

      <footer className="border-t border-surface-border py-4 text-center text-xs text-gray-600">
        Research Paper Finder · Built for OpenClaw Agent · NVIDIA NIM Free Tier
      </footer>
    </div>
  );
}
