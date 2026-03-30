import { useState, useEffect, useRef } from "react";
import { useMutation } from "@tanstack/react-query";
import { searchPapers, getSearchStatus } from "./api/client";
import SearchBar from "./components/SearchBar";
import ResultsGrid from "./components/ResultsGrid";
import ApiKeySetup from "./components/ApiKeySetup";
import { BookOpen, Cpu, LogOut, AlertCircle, Square, X } from "lucide-react";

function Header({ onLogout, onClear, showClear }) {
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
              <Cpu className="w-3 h-3" /> Powered by NVIDIA Nemotron
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {showClear && (
            <button
              onClick={onClear}
              className="flex items-center gap-1 text-gray-400 hover:text-white transition-colors text-xs px-3 py-1.5 rounded-md border border-surface-border hover:border-gray-500"
              title="Clear / New Search"
            >
              <X className="w-3 h-3" /> Clear
            </button>
          )}
          <button onClick={onLogout} className="text-gray-500 hover:text-gray-300 transition-colors" title="Logout">
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </header>
  );
}

const SECRET_CODE = "e3b6e625d9ab24982b84bba0d4792c7c";

function AccessDenied() {
  const [inputCode, setInputCode] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (inputCode === SECRET_CODE) {
      localStorage.setItem("rpf_access_granted", "true");
      window.location.reload();
    } else {
      setError("Invalid access code");
      setInputCode("");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface">
      <div className="card max-w-md w-full mx-4 space-y-6">
        <div className="text-center space-y-2">
          <h1 className="text-2xl font-bold text-white">Research Paper Finder</h1>
          <p className="text-gray-400">This tool requires an access code</p>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            type="password"
            placeholder="Enter access code"
            value={inputCode}
            onChange={(e) => { setInputCode(e.target.value); setError(""); }}
            className="w-full px-4 py-2 bg-surface-card border border-surface-border rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-brand"
          />
          {error && <div className="text-red-400 text-sm text-center">{error}</div>}
          <button type="submit" className="w-full px-4 py-2 bg-brand hover:bg-brand-light text-white font-medium rounded-lg transition-colors">
            Access
          </button>
        </form>
      </div>
    </div>
  );
}

export default function App() {
  const [accessGranted, setAccessGranted] = useState(() =>
    localStorage.getItem("rpf_access_granted") === "true"
  );
  const [apiKey, setApiKey] = useState(() => localStorage.getItem("rpf_api_key") || "");
  const [results, setResults] = useState(null);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState(null);
  const [progress, setProgress] = useState(null);
  const [progressPercent, setProgressPercent] = useState(0);
  const [activityLog, setActivityLog] = useState([]);
  const pollTimer = useRef(null);
  const logEndRef = useRef(null);

  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const key = urlParams.get("key");
    if (key === SECRET_CODE) {
      localStorage.setItem("rpf_access_granted", "true");
      setAccessGranted(true);
      urlParams.delete("key");
      const newUrl = window.location.pathname + (urlParams.toString() ? "?" + urlParams.toString() : "");
      window.history.replaceState({}, "", newUrl);
    }
    const token = urlParams.get("token");
    if (token) {
      localStorage.setItem("rpf_access_token", token);
      urlParams.delete("token");
      const newUrl = window.location.pathname + (urlParams.toString() ? "?" + urlParams.toString() : "");
      window.history.replaceState({}, "", newUrl);
    }
    return () => { if (pollTimer.current) clearTimeout(pollTimer.current); };
  }, []);

  // Auto-scroll activity log
  useEffect(() => {
    if (logEndRef.current) logEndRef.current.scrollIntoView({ behavior: "smooth" });
  }, [activityLog]);

  const addActivity = (msg) => {
    const time = new Date().toLocaleTimeString();
    setActivityLog((prev) => [...prev, { time, msg }]);
  };

  const startPolling = async (taskId) => {
    try {
      const data = await getSearchStatus(taskId);
      const newProgress = data.progress || null;

      // Add new progress messages to activity log
      if (newProgress && newProgress !== progress) {
        addActivity(newProgress);
      }

      setProgress(newProgress);
      setProgressPercent(data.progress_percent || 0);

      if (data.status === "completed") {
        setResults(data.result);
        setIsSearching(false);
        setProgress("Search completed!");
        setProgressPercent(100);
        addActivity("Search completed! Displaying results...");
      } else if (data.status === "failed") {
        setSearchError(data.error || "Search failed on server");
        setIsSearching(false);
        addActivity("Search failed: " + (data.error || "Unknown error"));
      } else {
        pollTimer.current = setTimeout(() => startPolling(taskId), 1500);
      }
    } catch (err) {
      setSearchError(err.response?.data?.detail || err.message);
      setIsSearching(false);
      addActivity("Error: " + (err.response?.data?.detail || err.message));
    }
  };

  const searchMutation = useMutation({
    mutationFn: searchPapers,
    onSuccess: (data) => {
      setSearchError(null);
      setResults(null);
      setIsSearching(true);
      setActivityLog([]);
      addActivity("Search started — generating search terms...");
      startPolling(data.task_id);
    },
    onError: (err) => {
      setSearchError(err.response?.data?.detail || err.message);
      addActivity("Error: " + (err.response?.data?.detail || err.message));
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

  const handleStop = () => {
    if (pollTimer.current) clearTimeout(pollTimer.current);
    setIsSearching(false);
    setProgress(null);
    setProgressPercent(0);
    addActivity("Search stopped by user.");
  };

  const handleClear = () => {
    if (pollTimer.current) clearTimeout(pollTimer.current);
    setResults(null);
    setIsSearching(false);
    setSearchError(null);
    setProgress(null);
    setProgressPercent(0);
    setActivityLog([]);
  };

  if (!accessGranted) return <AccessDenied />;
  if (!apiKey) return <ApiKeySetup onReady={setApiKey} />;

  return (
    <div className="min-h-screen flex flex-col">
      <Header onLogout={handleLogout} onClear={handleClear} showClear={results || searchError || isSearching || activityLog.length > 0} />

      <main className="flex-1 max-w-5xl mx-auto w-full px-4 py-8 space-y-8">
        {/* Hero */}
        {!results && !isSearching && !searchMutation.isPending && activityLog.length === 0 && (
          <div className="text-center space-y-3 py-8 fade-in">
            <h2 className="text-3xl font-bold text-white">Deep Research Paper Discovery</h2>
            <p className="text-gray-400 max-w-xl mx-auto">
              AI-powered search across arXiv, Semantic Scholar, and OpenAlex.
              LLM analyzes and scores every paper for relevance.
            </p>
            <div className="flex justify-center gap-4 text-sm text-gray-500 mt-2">
              <span>&#10003; Year filtering</span>
              <span>&#10003; Associated papers</span>
              <span>&#10003; PDF summaries</span>
              <span>&#10003; Relevance scoring</span>
            </div>
          </div>
        )}

        {/* Search */}
        <div className="flex justify-center">
          <SearchBar onSearch={searchMutation.mutate} loading={isSearching || searchMutation.isPending} />
        </div>

        {/* Loading state with live activity */}
        {(isSearching || searchMutation.isPending) && (
          <div className="space-y-4 fade-in">
            {/* Progress bar and stop button */}
            <div className="text-center space-y-3">
              <div className="w-10 h-10 spinner mx-auto" style={{ width: 40, height: 40 }} />
              <p className="text-white font-medium">Deep searching research papers...</p>
              <p className="text-gray-500 text-sm">
                {progress || "Generating search terms..."}
              </p>
              {progressPercent > 0 && (
                <div className="max-w-md mx-auto">
                  <div className="w-full h-2 bg-surface-border rounded-full overflow-hidden">
                    <div className="h-full bg-brand transition-all" style={{ width: `${progressPercent}%` }} />
                  </div>
                  <p className="text-xs text-gray-600 mt-1">{progressPercent}%</p>
                </div>
              )}
              {/* STOP BUTTON */}
              <button
                onClick={handleStop}
                className="mt-2 inline-flex items-center gap-2 px-4 py-2 bg-red-600/20 hover:bg-red-600/40 border border-red-600/50 text-red-400 hover:text-red-300 rounded-lg transition-colors text-sm font-medium"
              >
                <Square className="w-3.5 h-3.5" fill="currentColor" /> Stop Search
              </button>
            </div>

            {/* Live Activity Log */}
            {activityLog.length > 0 && (
              <div className="max-w-2xl mx-auto">
                <p className="text-xs text-gray-500 mb-2 font-medium uppercase tracking-wider">Live Activity</p>
                <div className="bg-surface-card border border-surface-border rounded-lg p-3 max-h-48 overflow-y-auto text-xs font-mono">
                  {activityLog.map((entry, i) => (
                    <div key={i} className="flex gap-2 py-0.5">
                      <span className="text-gray-600 whitespace-nowrap">[{entry.time}]</span>
                      <span className="text-gray-300">{entry.msg}</span>
                    </div>
                  ))}
                  <div ref={logEndRef} />
                </div>
              </div>
            )}
          </div>
        )}

        {/* Error */}
        {searchError && (
          <div className="max-w-3xl mx-auto card border-red-800/50 bg-red-900/10 flex items-start gap-3 fade-in">
            <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-red-300 font-medium">Search failed</p>
              <p className="text-red-400/80 text-sm mt-0.5">{searchError}</p>
            </div>
            <button onClick={handleClear} className="text-gray-500 hover:text-white">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Activity log when not searching (after stop) */}
        {!isSearching && !searchMutation.isPending && activityLog.length > 0 && !results && (
          <div className="max-w-2xl mx-auto">
            <p className="text-xs text-gray-500 mb-2 font-medium uppercase tracking-wider">Activity Log</p>
            <div className="bg-surface-card border border-surface-border rounded-lg p-3 max-h-48 overflow-y-auto text-xs font-mono">
              {activityLog.map((entry, i) => (
                <div key={i} className="flex gap-2 py-0.5">
                  <span className="text-gray-600 whitespace-nowrap">[{entry.time}]</span>
                  <span className="text-gray-300">{entry.msg}</span>
                </div>
              ))}
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
        Research Paper Finder &middot; NVIDIA NIM Free Tier
      </footer>
    </div>
  );
}
