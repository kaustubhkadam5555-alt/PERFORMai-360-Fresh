"use client";

import React, { useEffect, useState } from "react";

interface BiasFlagResponse {
  id: string;
  cycle_id: string;
  flag_type: string;
  explanation: string;
  severity: string;
  evidence_ids: string[];
  suggested_action?: string;
  status: string;
  reviewer_comment?: string;
  created_at: string;
  updated_at: string;
}

interface AuditSummaryResponse {
  cycle_id: string;
  total_flags: number;
  open_flags: number;
  acknowledged_flags: number;
  resolved_flags: number;
  not_applicable_flags: number;
  severity_breakdown: Record<string, number>;
  flag_type_breakdown: Record<string, number>;
  audit_health_score: number;
  is_ready_for_review: boolean;
  flags: BiasFlagResponse[];
}

interface ReviewCycleOption {
  id: string;
  title: string;
  employee_id: string;
  status: string;
}

export function AuditReviewCard() {
  const [cycles, setCycles] = useState<ReviewCycleOption[]>([]);
  const [selectedCycleId, setSelectedCycleId] = useState<string>("");
  const [summary, setSummary] = useState<AuditSummaryResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isLoadingCycles, setIsLoadingCycles] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [activeFlagForComment, setActiveFlagForComment] = useState<string | null>(null);
  const [commentText, setCommentText] = useState<string>("");

  const rawApiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const backendBaseUrl = rawApiUrl.replace(/\/api\/v1\/?$/, "").replace(/\/+$/, "");

  // Load available review cycles
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

  // Execute or refresh audit
  const runAudit = async () => {
    if (!selectedCycleId) return;
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const res = await fetch(`${backendBaseUrl}/api/v1/review-cycles/${selectedCycleId}/audit`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Viewer-Role": "manager",
        },
        body: JSON.stringify({ re_evaluate_all: false }),
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || `Audit execution returned HTTP ${res.status}`);
      }

      const data: AuditSummaryResponse = await res.json();
      setSummary(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setErrorMessage(msg);
    } finally {
      setIsLoading(false);
    }
  };

  const loadSummary = async () => {
    if (!selectedCycleId) return;
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const res = await fetch(`${backendBaseUrl}/api/v1/review-cycles/${selectedCycleId}/audit-summary`, {
        headers: { "X-Viewer-Role": "manager" },
        cache: "no-store",
      });

      if (!res.ok) {
        if (res.status === 404) {
          setSummary(null);
          setErrorMessage("No audit records found. Click 'Run Audit' to inspect this review cycle.");
          return;
        }
        throw new Error(`Failed to fetch audit summary: HTTP ${res.status}`);
      }

      const data: AuditSummaryResponse = await res.json();
      setSummary(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setErrorMessage(msg);
    } finally {
      setIsLoading(false);
    }
  };

  const updateFlagStatus = async (flagId: string, newStatus: string, comment?: string) => {
    if (!selectedCycleId) return;
    try {
      const res = await fetch(`${backendBaseUrl}/api/v1/review-cycles/${selectedCycleId}/audit-flags/${flagId}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          "X-Viewer-Role": "manager",
        },
        body: JSON.stringify({
          status: newStatus,
          reviewer_comment: comment || undefined,
        }),
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || `Failed updating flag: HTTP ${res.status}`);
      }

      setActiveFlagForComment(null);
      setCommentText("");
      await loadSummary();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setErrorMessage(msg);
    }
  };

  const filteredFlags = summary
    ? summary.flags.filter((f) => statusFilter === "all" || f.status === statusFilter)
    : [];

  return (
    <div id="bias-audit-panel" className="mt-14">
      <div className="rounded-2xl border border-purple-500/30 bg-slate-900/70 p-6 sm:p-8 backdrop-blur-md shadow-2xl">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-800 pb-6">
          <div>
            <div className="inline-flex items-center space-x-2 rounded-full border border-purple-500/30 bg-purple-500/10 px-3 py-1 text-xs font-semibold text-purple-300">
              <span className="h-1.5 w-1.5 rounded-full bg-purple-400"></span>
              <span>Phase 6 — Bias & Evidence-Quality Audit</span>
            </div>
            <h2 className="mt-3 text-2xl font-bold tracking-tight text-white sm:text-3xl">
              Deterministic Review Quality & Bias Audit
            </h2>
            <p className="mt-1 text-sm text-slate-400 max-w-2xl">
              Audits review cycles across five objective rules: Evidence Coverage, Recency Concentration,
              Stakeholder Coverage, Vague Claims, and Contradictory Feedback.
            </p>
          </div>

          {/* Controls */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
            {isLoadingCycles ? (
              <div className="text-xs text-slate-400 animate-pulse">Loading cycles...</div>
            ) : cycles.length > 0 ? (
              <select
                aria-label="Select Review Cycle for Audit"
                value={selectedCycleId}
                onChange={(e) => {
                  setSelectedCycleId(e.target.value);
                  setSummary(null);
                  setErrorMessage(null);
                }}
                className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-200 focus:border-purple-500 focus:outline-none"
              >
                {cycles.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.title} ({c.status})
                  </option>
                ))}
              </select>
            ) : (
              <div className="text-xs text-amber-400 bg-amber-500/10 px-3 py-2 rounded-lg border border-amber-500/30">
                No active cycles found.
              </div>
            )}

            <button
              onClick={runAudit}
              disabled={isLoading || !selectedCycleId}
              className="inline-flex items-center justify-center rounded-lg bg-purple-600 px-4 py-2 text-xs font-semibold text-white shadow-md hover:bg-purple-500 disabled:opacity-50 transition-colors"
            >
              {isLoading ? (
                <>
                  <svg className="animate-spin -ml-1 mr-2 h-3.5 w-3.5 text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
                  </svg>
                  Auditing Review...
                </>
              ) : (
                "Run Audit Check"
              )}
            </button>

            <button
              onClick={loadSummary}
              disabled={isLoading || !selectedCycleId}
              className="inline-flex items-center justify-center rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-2 text-xs font-semibold text-slate-300 hover:bg-slate-700 disabled:opacity-50 transition-colors"
            >
              Load Flags
            </button>
          </div>
        </div>

        {/* Ethical Governance Banner */}
        <div className="mt-6 flex items-start gap-3 rounded-xl border border-indigo-500/30 bg-indigo-500/10 p-4 text-xs text-indigo-200">
          <svg className="h-5 w-5 flex-shrink-0 text-indigo-400" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
          </svg>
          <div>
            <span className="font-bold uppercase tracking-wider text-indigo-300 block mb-0.5">
              Explainable Decision-Support Governance
            </span>
            <span>
              Audit flags are deterministic diagnostic checks highlighting potential evaluative imbalances, not definitive
              claims about personal intent or discrimination. Human evaluators must calibrate flags against complete context.
            </span>
          </div>
        </div>

        {/* Error notification */}
        {errorMessage && (
          <div className="mt-4 rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-xs text-rose-300">
            <span className="font-semibold block mb-0.5">Audit Notice:</span>
            {errorMessage}
          </div>
        )}

        {/* Audit Summary Display */}
        {summary && (
          <div className="mt-6 space-y-6">
            {/* Score & Metrics Bar */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3.5">
                <span className="text-[11px] font-medium text-slate-400 block">Review Health Score</span>
                <div className="flex items-baseline gap-1 mt-0.5">
                  <span className={`text-2xl font-black ${
                    summary.audit_health_score >= 0.85 ? "text-emerald-400" :
                    summary.audit_health_score >= 0.70 ? "text-amber-400" : "text-rose-400"
                  }`}>
                    {Math.round(summary.audit_health_score * 100)}%
                  </span>
                  <span className="text-[10px] text-slate-500 font-mono">/ 100%</span>
                </div>
              </div>

              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3.5">
                <span className="text-[11px] font-medium text-slate-400 block">Manager Review Status</span>
                <span className={`text-xs font-bold uppercase block mt-1 ${
                  summary.is_ready_for_review ? "text-emerald-400" : "text-amber-400"
                }`}>
                  {summary.is_ready_for_review ? "Ready for Calibration" : "High Severity Action Needed"}
                </span>
              </div>

              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3.5">
                <span className="text-[11px] font-medium text-slate-400 block">Open Audit Flags</span>
                <span className={`text-2xl font-black ${summary.open_flags > 0 ? "text-amber-400" : "text-slate-300"}`}>
                  {summary.open_flags}
                  <span className="text-xs font-normal text-slate-500 ml-1">/ {summary.total_flags}</span>
                </span>
              </div>

              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3.5">
                <span className="text-[11px] font-medium text-slate-400 block">Calibrated / Resolved</span>
                <span className="text-2xl font-black text-emerald-400">
                  {summary.acknowledged_flags + summary.resolved_flags}
                </span>
              </div>
            </div>

            {/* Filter Tabs */}
            <div className="flex border-b border-slate-800 space-x-3 text-xs">
              {[
                { id: "all", label: `All Flags (${summary.total_flags})` },
                { id: "open", label: `Open (${summary.open_flags})` },
                { id: "acknowledged", label: `Acknowledged (${summary.acknowledged_flags})` },
                { id: "resolved", label: `Resolved (${summary.resolved_flags})` },
                { id: "not_applicable", label: `Dismissed (${summary.not_applicable_flags})` },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setStatusFilter(tab.id)}
                  className={`pb-2.5 font-semibold transition-colors border-b-2 ${
                    statusFilter === tab.id
                      ? "border-purple-400 text-purple-400"
                      : "border-transparent text-slate-400 hover:text-slate-200"
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Flag List */}
            <div className="space-y-3">
              {filteredFlags.length === 0 ? (
                <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-6 text-center text-xs text-slate-400">
                  No flags matching filter &lsquo;{statusFilter}&rsquo;.
                </div>
              ) : (
                filteredFlags.map((flag) => (
                  <div key={flag.id} className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 space-y-3">
                    {/* Header line */}
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded font-bold border ${
                          flag.severity === "high" ? "bg-rose-500/10 text-rose-400 border-rose-500/30" :
                          flag.severity === "medium" ? "bg-amber-500/10 text-amber-400 border-amber-500/30" :
                          flag.severity === "review" ? "bg-purple-500/10 text-purple-400 border-purple-500/30" :
                          "bg-blue-500/10 text-blue-400 border-blue-500/30"
                        }`}>
                          {flag.severity}
                        </span>

                        <span className="text-xs font-mono font-semibold text-slate-200">
                          {flag.flag_type.replace(/_/g, " ")}
                        </span>
                      </div>

                      <span className={`text-[10px] font-mono px-2 py-0.5 rounded uppercase font-semibold ${
                        flag.status === "open" ? "bg-amber-500/10 text-amber-300" :
                        flag.status === "resolved" ? "bg-emerald-500/10 text-emerald-300" :
                        flag.status === "acknowledged" ? "bg-indigo-500/10 text-indigo-300" :
                        "bg-slate-800 text-slate-400"
                      }`}>
                        Status: {flag.status}
                      </span>
                    </div>

                    {/* Explanation */}
                    <p className="text-xs text-slate-300 leading-relaxed">
                      {flag.explanation}
                    </p>

                    {/* Suggested Action Box */}
                    {flag.suggested_action && (
                      <div className="rounded bg-slate-900/80 border border-slate-800 p-2.5 text-xs text-slate-300">
                        <span className="font-semibold text-purple-300 block mb-0.5">Suggested Action:</span>
                        {flag.suggested_action}
                      </div>
                    )}

                    {/* Reviewer Comment if exists */}
                    {flag.reviewer_comment && (
                      <div className="rounded bg-indigo-950/20 border border-indigo-500/20 p-2.5 text-xs text-indigo-200">
                        <span className="font-semibold text-indigo-400 block mb-0.5">Reviewer Calibration Note:</span>
                        {flag.reviewer_comment}
                      </div>
                    )}

                    {/* Action Bar */}
                    <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-800/80">
                      <div className="flex items-center gap-1.5">
                        {flag.status === "open" && (
                          <>
                            <button
                              onClick={() => {
                                setActiveFlagForComment(flag.id);
                                setCommentText("");
                              }}
                              className="text-[11px] font-semibold bg-indigo-600/80 hover:bg-indigo-500 text-white px-2.5 py-1 rounded transition-colors"
                            >
                              Acknowledge
                            </button>
                            <button
                              onClick={() => updateFlagStatus(flag.id, "resolved", "Resolved by reviewer")}
                              className="text-[11px] font-semibold bg-emerald-600/80 hover:bg-emerald-500 text-white px-2.5 py-1 rounded transition-colors"
                            >
                              Resolve
                            </button>
                            <button
                              onClick={() => updateFlagStatus(flag.id, "not_applicable", "Marked N/A by reviewer")}
                              className="text-[11px] text-slate-400 hover:text-slate-200 px-2 py-1 transition-colors"
                            >
                              Dismiss (N/A)
                            </button>
                          </>
                        )}
                        {flag.status !== "open" && (
                          <button
                            onClick={() => updateFlagStatus(flag.id, "open", "")}
                            className="text-[11px] text-slate-400 hover:text-slate-200 underline"
                          >
                            Reopen Flag
                          </button>
                        )}
                      </div>

                      {flag.evidence_ids && flag.evidence_ids.length > 0 && (
                        <div className="flex items-center gap-1">
                          <span className="text-[10px] text-slate-500">Related Evidence:</span>
                          {flag.evidence_ids.map((id) => (
                            <span key={id} className="text-[10px] font-mono bg-slate-800 text-slate-300 px-1 py-0.5 rounded">
                              {id.slice(0, 8)}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Inline Comment Box */}
                    {activeFlagForComment === flag.id && (
                      <div className="mt-2 p-3 bg-slate-900 rounded-lg border border-indigo-500/30 space-y-2">
                        <label className="text-[11px] font-semibold text-slate-300 block">
                          Reviewer Calibration Justification / Comment:
                        </label>
                        <textarea
                          rows={2}
                          value={commentText}
                          onChange={(e) => setCommentText(e.target.value)}
                          placeholder="Note context discussed with committee..."
                          className="w-full text-xs bg-slate-950 border border-slate-700 rounded p-2 text-slate-200 focus:outline-none focus:border-indigo-500"
                        />
                        <div className="flex justify-end gap-2">
                          <button
                            onClick={() => setActiveFlagForComment(null)}
                            className="text-[11px] text-slate-400 px-2 py-1"
                          >
                            Cancel
                          </button>
                          <button
                            onClick={() => updateFlagStatus(flag.id, "acknowledged", commentText)}
                            className="text-[11px] font-semibold bg-indigo-600 hover:bg-indigo-500 text-white px-3 py-1 rounded"
                          >
                            Save Calibration
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
