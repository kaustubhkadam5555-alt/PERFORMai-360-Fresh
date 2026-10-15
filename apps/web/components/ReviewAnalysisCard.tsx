"use client";

import React, { useEffect, useState } from "react";

interface EvidenceAnalysisSummary {
  total_evidence_examined: number;
  source_distribution: Record<string, number>;
  period_start: string;
  period_end: string;
  completeness_score: number;
  detected_gaps: string[];
  cited_evidence_ids: string[];
}

interface StrengthItem {
  title: string;
  description: string;
  supporting_evidence_ids: string[];
  excerpts: string[];
  confidence: string;
  limitations: string[];
}

interface ImprovementOpportunity {
  title: string;
  gap_observed: string;
  supporting_evidence_ids: string[];
  missing_context?: string;
  development_suggestion: string;
}

interface ContradictionItem {
  topic: string;
  observation_a: string;
  evidence_ids_a: string[];
  observation_b: string;
  evidence_ids_b: string[];
  missing_context?: string;
  uncertainty_note?: string;
}

interface DiscussionQuestion {
  category: string;
  question: string;
  context: string;
}

interface ReviewAnalysisResponse {
  analysis_id: string;
  cycle_id: string;
  employee_id: string;
  status: string;
  timestamp: string;
  prompt_version: string;
  provider: string;
  model: string;
  evidence_summary: EvidenceAnalysisSummary;
  strengths: StrengthItem[];
  improvement_opportunities: ImprovementOpportunity[];
  contradictions: ContradictionItem[];
  suggested_discussion_questions: DiscussionQuestion[];
  overall_limitations: string[];
  requires_human_review: boolean;
  human_review_notice: string;
}

interface ReviewCycleOption {
  id: string;
  title: string;
  employee_id: string;
  status: string;
}

export function ReviewAnalysisCard() {
  const [cycles, setCycles] = useState<ReviewCycleOption[]>([]);
  const [selectedCycleId, setSelectedCycleId] = useState<string>("");
  const [analysis, setAnalysis] = useState<ReviewAnalysisResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isLoadingCycles, setIsLoadingCycles] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"strengths" | "improvements" | "contradictions" | "questions">("strengths");

  const rawApiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const backendBaseUrl = rawApiUrl.replace(/\/api\/v1\/?$/, "").replace(/\/+$/, "");

  // Load available review cycles on mount
  useEffect(() => {
    async function fetchCycles() {
      setIsLoadingCycles(true);
      try {
        const res = await fetch(`${backendBaseUrl}/api/v1/review-cycles?limit=20`, { cache: "no-store" });
        if (res.ok) {
          const data: ReviewCycleOption[] = await res.json();
          setCycles(data);
          setSelectedCycleId((prev) => prev || (data.length > 0 ? data[0].id : ""));
        }
      } catch (err) {
        console.warn("Could not load review cycles:", err);
      } finally {
        setIsLoadingCycles(false);
      }
    }
    fetchCycles();
  }, [backendBaseUrl]);

  // Fetch latest analysis or trigger new analysis
  const runAnalysis = async () => {
    if (!selectedCycleId) return;
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const res = await fetch(`${backendBaseUrl}/api/v1/review-cycles/${selectedCycleId}/analysis`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Viewer-Role": "manager",
        },
        body: JSON.stringify({
          max_evidence_items: 50,
          include_draft_report: true,
        }),
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || `Analysis execution returned HTTP ${res.status}`);
      }

      const data: ReviewAnalysisResponse = await res.json();
      setAnalysis(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setErrorMessage(msg);
    } finally {
      setIsLoading(false);
    }
  };

  const loadLatestAnalysis = async () => {
    if (!selectedCycleId) return;
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const res = await fetch(`${backendBaseUrl}/api/v1/review-cycles/${selectedCycleId}/analysis`, {
        headers: { "X-Viewer-Role": "manager" },
        cache: "no-store",
      });

      if (!res.ok) {
        if (res.status === 404) {
          setAnalysis(null);
          setErrorMessage("No previous analysis found for this review cycle. Click 'Run Analysis' to generate one.");
          return;
        }
        throw new Error(`Failed to fetch analysis: HTTP ${res.status}`);
      }

      const data: ReviewAnalysisResponse = await res.json();
      setAnalysis(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setErrorMessage(msg);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div id="ai-review-analysis" className="mt-14">
      <div className="rounded-2xl border border-indigo-500/30 bg-slate-900/70 p-6 sm:p-8 backdrop-blur-md shadow-2xl">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-800 pb-6">
          <div>
            <div className="inline-flex items-center space-x-2 rounded-full border border-indigo-500/30 bg-indigo-500/10 px-3 py-1 text-xs font-semibold text-indigo-300">
              <span className="h-1.5 w-1.5 rounded-full bg-indigo-400"></span>
              <span>Phase 5 — Single-Pass AI Analysis</span>
            </div>
            <h2 className="mt-3 text-2xl font-bold tracking-tight text-white sm:text-3xl">
              Evidence-Grounded Review Insights
            </h2>
            <p className="mt-1 text-sm text-slate-400 max-w-2xl">
              Generates traceable, balanced performance observations strictly citing verified evidence.
              Consequential promotion, rating, and compensation decisions remain strictly under human manager governance.
            </p>
          </div>

          {/* Controls */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
            {isLoadingCycles ? (
              <div className="text-xs text-slate-400 animate-pulse">Loading cycles...</div>
            ) : cycles.length > 0 ? (
              <select
                aria-label="Select Review Cycle"
                value={selectedCycleId}
                onChange={(e) => {
                  setSelectedCycleId(e.target.value);
                  setAnalysis(null);
                  setErrorMessage(null);
                }}
                className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
              >
                {cycles.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.title} ({c.status})
                  </option>
                ))}
              </select>
            ) : (
              <div className="text-xs text-amber-400 bg-amber-500/10 px-3 py-2 rounded-lg border border-amber-500/30">
                No active cycles found. Seed or create a cycle via API.
              </div>
            )}

            <button
              onClick={runAnalysis}
              disabled={isLoading || !selectedCycleId}
              className="inline-flex items-center justify-center rounded-lg bg-indigo-600 px-4 py-2 text-xs font-semibold text-white shadow-md hover:bg-indigo-500 disabled:opacity-50 transition-colors"
            >
              {isLoading ? (
                <>
                  <svg className="animate-spin -ml-1 mr-2 h-3.5 w-3.5 text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
                  </svg>
                  Analyzing Evidence...
                </>
              ) : (
                "Run Analysis"
              )}
            </button>

            <button
              onClick={loadLatestAnalysis}
              disabled={isLoading || !selectedCycleId}
              className="inline-flex items-center justify-center rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-2 text-xs font-semibold text-slate-300 hover:bg-slate-700 disabled:opacity-50 transition-colors"
            >
              Load Latest
            </button>
          </div>
        </div>

        {/* Human in the loop mandatory banner */}
        <div className="mt-6 flex items-start gap-3 rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-xs text-amber-200">
          <svg className="h-5 w-5 flex-shrink-0 text-amber-400" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
          <div>
            <span className="font-bold uppercase tracking-wider text-amber-300 block mb-0.5">
              Human Reviewer Responsibility Notice
            </span>
            <span>
              This AI-generated analysis is an evidence-grounded decision support draft.
              PERFORMai-360 strictly forbids automated employee rankings, compensation adjustments, or performance scores.
              The authorized human manager must independently verify observations before completing reviews.
            </span>
          </div>
        </div>

        {/* Error notification */}
        {errorMessage && (
          <div className="mt-4 rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-xs text-rose-300">
            <span className="font-semibold block mb-0.5">Notice:</span>
            {errorMessage}
          </div>
        )}

        {/* Analysis Output View */}
        {analysis && (
          <div className="mt-6 space-y-6">
            {/* Status & Metadata Bar */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
                <span className="text-[11px] font-medium text-slate-400 block">Status</span>
                <span className={`text-sm font-bold uppercase ${
                  analysis.status === "completed" ? "text-emerald-400" :
                  analysis.status === "insufficient_evidence" ? "text-amber-400" : "text-rose-400"
                }`}>
                  {analysis.status}
                </span>
              </div>
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
                <span className="text-[11px] font-medium text-slate-400 block">AI Provider / Model</span>
                <span className="text-xs font-mono font-semibold text-slate-200 truncate block">
                  {analysis.provider} ({analysis.model})
                </span>
              </div>
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
                <span className="text-[11px] font-medium text-slate-400 block">Evidence Examined</span>
                <span className="text-sm font-bold text-slate-200">
                  {analysis.evidence_summary.total_evidence_examined} items
                </span>
              </div>
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
                <span className="text-[11px] font-medium text-slate-400 block">Completeness Score</span>
                <span className="text-sm font-bold text-indigo-300">
                  {Math.round(analysis.evidence_summary.completeness_score * 100)}%
                </span>
              </div>
            </div>

            {/* Evidence Completeness Gaps, if any */}
            {analysis.evidence_summary.detected_gaps.length > 0 && (
              <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-4 text-xs">
                <span className="font-semibold text-slate-300 block mb-1">Detected Evidence Gaps:</span>
                <ul className="list-disc list-inside space-y-0.5 text-slate-400">
                  {analysis.evidence_summary.detected_gaps.map((gap, i) => (
                    <li key={i}>{gap}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Content Tabs */}
            <div className="flex border-b border-slate-800 space-x-4 text-xs">
              <button
                onClick={() => setActiveTab("strengths")}
                className={`pb-2.5 font-semibold transition-colors border-b-2 ${
                  activeTab === "strengths"
                    ? "border-emerald-400 text-emerald-400"
                    : "border-transparent text-slate-400 hover:text-slate-200"
                }`}
              >
                Grounded Strengths ({analysis.strengths.length})
              </button>
              <button
                onClick={() => setActiveTab("improvements")}
                className={`pb-2.5 font-semibold transition-colors border-b-2 ${
                  activeTab === "improvements"
                    ? "border-amber-400 text-amber-400"
                    : "border-transparent text-slate-400 hover:text-slate-200"
                }`}
              >
                Development Areas ({analysis.improvement_opportunities.length})
              </button>
              <button
                onClick={() => setActiveTab("contradictions")}
                className={`pb-2.5 font-semibold transition-colors border-b-2 ${
                  activeTab === "contradictions"
                    ? "border-purple-400 text-purple-400"
                    : "border-transparent text-slate-400 hover:text-slate-200"
                }`}
              >
                Contradictions & Uncertainty ({analysis.contradictions.length})
              </button>
              <button
                onClick={() => setActiveTab("questions")}
                className={`pb-2.5 font-semibold transition-colors border-b-2 ${
                  activeTab === "questions"
                    ? "border-indigo-400 text-indigo-400"
                    : "border-transparent text-slate-400 hover:text-slate-200"
                }`}
              >
                Discussion Questions ({analysis.suggested_discussion_questions.length})
              </button>
            </div>

            {/* Tab Panels */}
            {activeTab === "strengths" && (
              <div className="space-y-3">
                {analysis.strengths.length === 0 ? (
                  <p className="text-xs text-slate-400 italic">No grounded strengths observed in available evidence.</p>
                ) : (
                  analysis.strengths.map((s, idx) => (
                    <div key={idx} className="rounded-xl border border-slate-800 bg-slate-950/50 p-4 space-y-2">
                      <div className="flex items-center justify-between">
                        <h4 className="text-sm font-semibold text-white">{s.title}</h4>
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                          {s.confidence} confidence
                        </span>
                      </div>
                      <p className="text-xs text-slate-300">{s.description}</p>
                      {s.excerpts.length > 0 && (
                        <div className="rounded bg-slate-900/60 p-2 text-[11px] text-slate-400 border-l-2 border-emerald-500">
                          &ldquo;{s.excerpts[0]}&rdquo;
                        </div>
                      )}
                      <div className="flex flex-wrap gap-1.5 pt-1">
                        <span className="text-[10px] text-slate-500 self-center">Evidence Citations:</span>
                        {s.supporting_evidence_ids.map((id) => (
                          <span key={id} className="text-[10px] font-mono bg-slate-800 text-slate-300 px-1.5 py-0.5 rounded">
                            {id.slice(0, 8)}...
                          </span>
                        ))}
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}

            {activeTab === "improvements" && (
              <div className="space-y-3">
                {analysis.improvement_opportunities.length === 0 ? (
                  <p className="text-xs text-slate-400 italic">No improvement gaps identified in evidence.</p>
                ) : (
                  analysis.improvement_opportunities.map((imp, idx) => (
                    <div key={idx} className="rounded-xl border border-slate-800 bg-slate-950/50 p-4 space-y-2">
                      <h4 className="text-sm font-semibold text-white">{imp.title}</h4>
                      <p className="text-xs text-slate-300">{imp.gap_observed}</p>
                      <div className="rounded bg-indigo-950/30 border border-indigo-500/20 p-2.5 text-xs text-indigo-300">
                        <span className="font-semibold block mb-0.5">Development Suggestion:</span>
                        {imp.development_suggestion}
                      </div>
                      {imp.missing_context && (
                        <p className="text-[11px] text-slate-400 italic">Context Gap: {imp.missing_context}</p>
                      )}
                    </div>
                  ))
                )}
              </div>
            )}

            {activeTab === "contradictions" && (
              <div className="space-y-3">
                {analysis.contradictions.length === 0 ? (
                  <p className="text-xs text-slate-400 italic">No contradictory signals identified across evidence records.</p>
                ) : (
                  analysis.contradictions.map((c, idx) => (
                    <div key={idx} className="rounded-xl border border-slate-800 bg-slate-950/50 p-4 space-y-2">
                      <h4 className="text-sm font-semibold text-purple-300">{c.topic}</h4>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                        <div className="p-2.5 rounded bg-slate-900/60 border border-slate-800">
                          <span className="text-slate-400 block font-semibold mb-1">Signal A</span>
                          <p className="text-slate-200">{c.observation_a}</p>
                        </div>
                        <div className="p-2.5 rounded bg-slate-900/60 border border-slate-800">
                          <span className="text-slate-400 block font-semibold mb-1">Signal B</span>
                          <p className="text-slate-200">{c.observation_b}</p>
                        </div>
                      </div>
                      {c.uncertainty_note && (
                        <p className="text-[11px] text-amber-300/80 italic">Uncertainty Note: {c.uncertainty_note}</p>
                      )}
                    </div>
                  ))
                )}
              </div>
            )}

            {activeTab === "questions" && (
              <div className="space-y-3">
                {analysis.suggested_discussion_questions.length === 0 ? (
                  <p className="text-xs text-slate-400 italic">No discussion questions generated.</p>
                ) : (
                  analysis.suggested_discussion_questions.map((q, idx) => (
                    <div key={idx} className="rounded-xl border border-slate-800 bg-slate-950/50 p-4 space-y-1.5">
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                          {q.category}
                        </span>
                        <h4 className="text-xs font-semibold text-slate-200">{q.question}</h4>
                      </div>
                      <p className="text-[11px] text-slate-400">{q.context}</p>
                    </div>
                  ))
                )}
              </div>
            )}

            {/* Overall Limitations Footer */}
            {analysis.overall_limitations.length > 0 && (
              <div className="rounded-xl border border-slate-800 bg-slate-950/30 p-3 text-[11px] text-slate-500 space-y-1">
                <span className="font-semibold block text-slate-400">Analysis Scope & Limitations:</span>
                <ul className="list-disc list-inside space-y-0.5">
                  {analysis.overall_limitations.map((lim, i) => (
                    <li key={i}>{lim}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
