"use client";

import React, { useEffect, useState } from "react";

interface DependencyState {
  status: string;
  message?: string;
  provider?: string;
  mode?: string;
}

interface ReadinessData {
  status: string;
  app: string;
  version: string;
  environment: string;
  dependencies?: {
    database?: DependencyState;
    llm_provider?: DependencyState;
  };
}

interface LivenessData {
  status: string;
  app: string;
  version: string;
  environment: string;
}

export function BackendHealthCard() {
  const [liveness, setLiveness] = useState<LivenessData | null>(null);
  const [readiness, setReadiness] = useState<ReadinessData | null>(null);
  const [latencyMs, setLatencyMs] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [lastChecked, setLastChecked] = useState<string | null>(null);
  const [showJson, setShowJson] = useState<boolean>(false);

  // Configurable Backend URL from environment with local fallback
  const rawApiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  // Normalize by stripping trailing slashes or /api/v1 suffix to reach root /health & /health/ready
  const backendBaseUrl = rawApiUrl.replace(/\/api\/v1\/?$/, "").replace(/\/+$/, "");

  const executeProbe = async () => {
    setIsLoading(true);
    setErrorMessage(null);
    const startTime = performance.now();

    try {
      // 1. Fetch liveness probe (/health)
      const liveRes = await fetch(`${backendBaseUrl}/health`, {
        cache: "no-store",
      });

      if (!liveRes.ok) {
        throw new Error(`Liveness probe returned HTTP ${liveRes.status}`);
      }
      const liveJson: LivenessData = await liveRes.json();
      setLiveness(liveJson);

      // 2. Fetch readiness probe (/health/ready)
      const readyRes = await fetch(`${backendBaseUrl}/health/ready`, {
        cache: "no-store",
      });
      const readyJson: ReadinessData = await readyRes.json();
      setReadiness(readyJson);

      const endTime = performance.now();
      setLatencyMs(Math.round(endTime - startTime));
      setLastChecked(new Date().toLocaleTimeString());

      if (!readyRes.ok && readyRes.status !== 503) {
        throw new Error(`Readiness probe returned HTTP ${readyRes.status}`);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to connect to backend service";
      setErrorMessage(msg);
      setLiveness(null);
      setReadiness(null);
      setLatencyMs(null);
      setLastChecked(new Date().toLocaleTimeString());
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    let isSubscribed = true;
    const startTime = performance.now();

    Promise.all([
      fetch(`${backendBaseUrl}/health`, { cache: "no-store" })
        .then(async (res) => {
          if (!res.ok) throw new Error(`Liveness HTTP ${res.status}`);
          return (await res.json()) as LivenessData;
        }),
      fetch(`${backendBaseUrl}/health/ready`, { cache: "no-store" })
        .then(async (res) => (await res.json()) as ReadinessData)
        .catch(() => null),
    ])
      .then(([liveData, readyData]) => {
        if (!isSubscribed) return;
        setLiveness(liveData);
        setReadiness(readyData);
        setLatencyMs(Math.round(performance.now() - startTime));
        setLastChecked(new Date().toLocaleTimeString());
        setIsLoading(false);
      })
      .catch((err: unknown) => {
        if (!isSubscribed) return;
        const msg = err instanceof Error ? err.message : "Backend connection probe failed";
        setErrorMessage(msg);
        setLastChecked(new Date().toLocaleTimeString());
        setIsLoading(false);
      });

    return () => {
      isSubscribed = false;
    };
  }, [backendBaseUrl]);

  const isConnected = liveness !== null;
  const isDbReady = readiness?.dependencies?.database?.status === "ready";

  return (
    <div id="health" className="glass-panel rounded-2xl p-6 sm:p-8">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-slate-800/80 pb-6">
        <div>
          <div className="flex items-center space-x-3">
            <h2 className="text-xl font-bold text-white sm:text-2xl">
              System Health & Service Probes
            </h2>
            {isLoading ? (
              <span className="inline-flex items-center rounded-full bg-slate-800 px-2.5 py-1 text-xs font-medium text-slate-300">
                <svg
                  className="mr-1.5 h-3 w-3 animate-spin text-slate-400"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                  />
                </svg>
                Probing...
              </span>
            ) : isConnected && isDbReady ? (
              <span className="inline-flex items-center rounded-full bg-emerald-500/10 border border-emerald-500/30 px-2.5 py-1 text-xs font-semibold text-emerald-400">
                <span className="mr-1.5 h-2 w-2 rounded-full bg-emerald-400"></span>
                Fully Operational
              </span>
            ) : isConnected ? (
              <span className="inline-flex items-center rounded-full bg-amber-500/10 border border-amber-500/30 px-2.5 py-1 text-xs font-semibold text-amber-400">
                <span className="mr-1.5 h-2 w-2 rounded-full bg-amber-400"></span>
                Degraded (Check Database)
              </span>
            ) : (
              <span className="inline-flex items-center rounded-full bg-rose-500/10 border border-rose-500/30 px-2.5 py-1 text-xs font-semibold text-rose-400">
                <span className="mr-1.5 h-2 w-2 rounded-full bg-rose-400"></span>
                Disconnected
              </span>
            )}
          </div>
          <p className="mt-1 text-sm text-slate-400">
            Real-time verification of FastAPI backend, PostgreSQL persistence, and offline AI adapter.
          </p>
        </div>

        {/* Action Button */}
        <div className="flex items-center space-x-3">
          <button
            onClick={executeProbe}
            disabled={isLoading}
            className="inline-flex items-center justify-center rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition-all hover:bg-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 disabled:opacity-50 cursor-pointer"
          >
            <svg
              className={`mr-2 h-4 w-4 ${isLoading ? "animate-spin" : ""}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
            Probe Health
          </button>
        </div>
      </div>

      {/* Target URL Info */}
      <div className="mt-4 flex flex-wrap items-center justify-between gap-2 rounded-lg bg-slate-900/60 px-4 py-2 text-xs font-mono text-slate-400 border border-slate-800">
        <div>
          <span className="text-slate-500">Target Endpoint: </span>
          <span className="text-indigo-300 font-semibold">{backendBaseUrl}</span>
        </div>
        <div>
          <span className="text-slate-500">Last Checked: </span>
          <span>{lastChecked || "Never"}</span>
          {latencyMs !== null && (
            <span className="ml-2 rounded bg-slate-800 px-1.5 py-0.5 text-slate-300">
              {latencyMs} ms
            </span>
          )}
        </div>
      </div>

      {/* Error Banner */}
      {errorMessage && (
        <div className="mt-6 rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-300">
          <div className="flex items-start space-x-3">
            <svg
              className="h-5 w-5 flex-shrink-0 text-rose-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <div>
              <p className="font-semibold text-rose-200">Connection probe failed</p>
              <p className="mt-1 text-xs text-rose-300/80">{errorMessage}</p>
              <div className="mt-3 text-xs text-slate-300">
                <span className="font-semibold text-white">Troubleshooting steps:</span>
                <ul className="mt-1 list-disc list-inside space-y-0.5 text-slate-400">
                  <li>Ensure FastAPI backend is running: <code className="bg-slate-900 px-1 py-0.5 rounded text-indigo-300">uvicorn app.main:app --port 8000</code></li>
                  <li>Ensure PostgreSQL is up: <code className="bg-slate-900 px-1 py-0.5 rounded text-indigo-300">docker compose up -d</code></li>
                  <li>Verify <code className="bg-slate-900 px-1 py-0.5 rounded text-indigo-300">NEXT_PUBLIC_API_URL</code> points to <code className="text-indigo-300">http://localhost:8000</code></li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Grid of Probes */}
      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        {/* Probe 1: FastAPI API Process */}
        <div className="glass-panel rounded-xl p-5 border border-slate-800">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              API Process
            </span>
            {isConnected ? (
              <span className="flex h-2.5 w-2.5 rounded-full bg-emerald-500"></span>
            ) : (
              <span className="flex h-2.5 w-2.5 rounded-full bg-rose-500"></span>
            )}
          </div>
          <div className="mt-3">
            <p className="text-lg font-bold text-white">
              {isConnected ? "Active (200 OK)" : "Offline"}
            </p>
            <p className="text-xs text-slate-400 mt-1">
              {isConnected
                ? `${liveness?.app} v${liveness?.version} (${liveness?.environment})`
                : "FastAPI server unreachable"}
            </p>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-800/80 text-xs text-slate-400 flex justify-between">
            <span>Probe:</span>
            <code className="text-indigo-400 font-mono">GET /health</code>
          </div>
        </div>

        {/* Probe 2: PostgreSQL Database */}
        <div className="glass-panel rounded-xl p-5 border border-slate-800">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              PostgreSQL Database
            </span>
            {isDbReady ? (
              <span className="flex h-2.5 w-2.5 rounded-full bg-emerald-500"></span>
            ) : (
              <span className="flex h-2.5 w-2.5 rounded-full bg-amber-500"></span>
            )}
          </div>
          <div className="mt-3">
            <p className="text-lg font-bold text-white">
              {isDbReady ? "Connected" : "Disconnected"}
            </p>
            <p className="text-xs text-slate-400 mt-1 truncate">
              {readiness?.dependencies?.database?.message || "No database probe response"}
            </p>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-800/80 text-xs text-slate-400 flex justify-between">
            <span>Volume / Port:</span>
            <span className="font-mono text-slate-300">pgdata / 5433</span>
          </div>
        </div>

        {/* Probe 3: AI Provider Mode */}
        <div className="glass-panel rounded-xl p-5 border border-slate-800">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              AI Provider Adapter
            </span>
            <span className="flex h-2.5 w-2.5 rounded-full bg-indigo-500"></span>
          </div>
          <div className="mt-3">
            <p className="text-lg font-bold text-white">
              {readiness?.dependencies?.llm_provider?.provider?.toUpperCase() || "MOCK"}
            </p>
            <p className="text-xs text-slate-400 mt-1">
              Offline deterministic mock provider (zero API costs)
            </p>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-800/80 text-xs text-slate-400 flex justify-between">
            <span>Status:</span>
            <span className="font-mono text-emerald-400">Safe Offline</span>
          </div>
        </div>
      </div>

      {/* Collapsible Raw JSON Response */}
      {(liveness || readiness) && (
        <div className="mt-6">
          <button
            onClick={() => setShowJson(!showJson)}
            className="flex items-center text-xs font-medium text-slate-400 hover:text-slate-200 transition-colors cursor-pointer"
          >
            <svg
              className={`mr-1.5 h-3.5 w-3.5 transform transition-transform ${
                showJson ? "rotate-90" : ""
              }`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
            {showJson ? "Hide Raw Health Payloads" : "Inspect Raw Health Payloads"}
          </button>

          {showJson && (
            <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2 text-xs font-mono">
              <div className="rounded-xl bg-slate-900/90 p-3 border border-slate-800">
                <span className="text-slate-400 font-semibold block mb-1">GET /health</span>
                <pre className="text-slate-300 overflow-x-auto">
                  {JSON.stringify(liveness, null, 2)}
                </pre>
              </div>
              <div className="rounded-xl bg-slate-900/90 p-3 border border-slate-800">
                <span className="text-slate-400 font-semibold block mb-1">GET /health/ready</span>
                <pre className="text-slate-300 overflow-x-auto">
                  {JSON.stringify(readiness, null, 2)}
                </pre>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
