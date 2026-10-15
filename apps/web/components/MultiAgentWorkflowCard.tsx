"use client";

import React, { useEffect, useState } from "react";

interface WorkflowStageStatus {
  stage_name: string;
  display_title: string;
  status: string;
  description: string;
  summary_data?: Record<string, unknown>;
  completed_at?: string;
}

interface WorkflowDraftReport {
  cycle_id: string;
  employee_id: string;
  version_number: number;
  status: string;
  executive_summary: string;
  strengths: Array<{
    title: string;
    description: string;
    supporting_evidence_ids?: string[];
    confidence?: string;
    excerpts?: string[];
  }>;
  growth_areas: Array<{
    title?: string;
    gap_observed?: string;
    development_suggestion?: string;
    missing_context?: string;
    supporting_evidence_ids?: string[];
  }>;
  goal_progress: Array<{
    id: string;
    description: string;
    status: string;
    measurable_target?: string;
    outcome_notes?: string;
  }>;
  impact_highlights: Array<{
    title: string;
    impact_summary: string;
    citations?: string[];
  }>;
  bias_audit_summary: {
    health_score?: number;
    is_ready_for_review?: boolean;
    severity_breakdown?: Record<string, number>;
    total_flags?: number;
  };
  evidence_gaps_and_limitations: string[];
  suggested_discussion_questions: Array<string | { category?: string; question?: string; context?: string }>;
  citations: string[];
  created_at?: string;
}

interface WorkflowStatusResponse {
  run_id: string;
  cycle_id: string;
  employee_id?: string;
  workflow_status: string;
  current_stage: string;
  stages: WorkflowStageStatus[];
  draft_report?: WorkflowDraftReport;
  audit_health_score?: number;
  available_actions: string[];
  approval_metadata?: {
    decision?: string;
    reviewer_id?: string;
    reviewer_role?: string;
    reviewer_comments?: string;
    comments?: string;
    approval_timestamp?: string;
  };
  errors: string[];
  created_at: string;
  updated_at: string;
}

interface ReviewCycleOption {
  id: string;
  title: string;
  employee_id: string;
  status: string;
}

export function MultiAgentWorkflowCard() {
  const [cycles, setCycles] = useState<ReviewCycleOption[]>([]);
  const [selectedCycleId, setSelectedCycleId] = useState<string>("");
  const [viewerRole, setViewerRole] = useState<string>("manager");
  const [workflowStatus, setWorkflowStatus] = useState<WorkflowStatusResponse | null>(null);
  const [isLoadingCycles, setIsLoadingCycles] = useState<boolean>(true);
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [isActionLoading, setIsActionLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"summary" | "strengths" | "growth" | "goals" | "audit" | "questions">("summary");

  // Approval / Revision dialog state
  const [modalMode, setModalMode] = useState<"approve" | "revision" | "cancel" | null>(null);
  const [actionComments, setActionComments] = useState<string>("");

  const rawApiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const backendBaseUrl = rawApiUrl.replace(/\/api\/v1\/?$/, "").replace(/\/+$/, "");

  // Fetch cycles on mount
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

  // Check for existing active workflow when selected cycle changes
  useEffect(() => {
    if (!selectedCycleId) return;
    async function checkActiveWorkflow() {
      try {
        const res = await fetch(`${backendBaseUrl}/api/v1/review-cycles/${selectedCycleId}/workflows`, {
          headers: { "X-Viewer-Role": viewerRole },
          cache: "no-store",
        });
        if (res.ok) {
          const listData = await res.json();
          if (listData.items && listData.items.length > 0) {
            setWorkflowStatus(listData.items[0]);
          } else {
            setWorkflowStatus(null);
          }
        }
      } catch (err) {
        console.warn("Could not check active workflow for cycle:", err);
      }
    }
    checkActiveWorkflow();
  }, [selectedCycleId, viewerRole, backendBaseUrl]);

  // Start workflow run
  const handleStartWorkflow = async (force: boolean = false) => {
    if (!selectedCycleId) return;
    setIsRunning(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      const res = await fetch(`${backendBaseUrl}/api/v1/review-cycles/${selectedCycleId}/workflows`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Viewer-Role": viewerRole,
        },
        body: JSON.stringify({ force_re_run: force, max_evidence_items: 50 }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Failed to start workflow: HTTP ${res.status}`);
      }

      const data: WorkflowStatusResponse = await res.json();
      setWorkflowStatus(data);
      setSuccessMessage(
        data.workflow_status === "awaiting_approval"
          ? "Workflow completed initial stages and safely paused at Human Approval boundary."
          : `Workflow transitioned to '${data.workflow_status}'.`
      );
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to execute multi-agent workflow.";
      setErrorMessage(msg);
    } finally {
      setIsRunning(false);
    }
  };

  // Submit Approval
  const handleApprove = async () => {
    if (!workflowStatus) return;
    setIsActionLoading(true);
    setErrorMessage(null);
    try {
      const res = await fetch(`${backendBaseUrl}/api/v1/workflows/${workflowStatus.run_id}/approve`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Viewer-Role": viewerRole,
        },
        body: JSON.stringify({ comments: actionComments || "Approved by reviewer." }),
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Approval failed: HTTP ${res.status}`);
      }
      const data: WorkflowStatusResponse = await res.json();
      setWorkflowStatus(data);
      setModalMode(null);
      setActionComments("");
      setSuccessMessage("Performance review report approved and finalized with full audit log.");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error submitting approval.";
      setErrorMessage(msg);
    } finally {
      setIsActionLoading(false);
    }
  };

  // Submit Revision Request
  const handleRequestRevision = async () => {
    if (!workflowStatus) return;
    if (!actionComments.trim()) {
      setErrorMessage("Revision instructions are required.");
      return;
    }
    setIsActionLoading(true);
    setErrorMessage(null);
    try {
      const res = await fetch(`${backendBaseUrl}/api/v1/workflows/${workflowStatus.run_id}/request-revision`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Viewer-Role": viewerRole,
        },
        body: JSON.stringify({ comments: actionComments }),
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Revision request failed: HTTP ${res.status}`);
      }
      const data: WorkflowStatusResponse = await res.json();
      setWorkflowStatus(data);
      setModalMode(null);
      setActionComments("");
      setSuccessMessage("Revision request recorded. Report marked for review updates.");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error requesting revision.";
      setErrorMessage(msg);
    } finally {
      setIsActionLoading(false);
    }
  };

  // Submit Cancellation
  const handleCancelWorkflow = async () => {
    if (!workflowStatus) return;
    setIsActionLoading(true);
    setErrorMessage(null);
    try {
      const res = await fetch(`${backendBaseUrl}/api/v1/workflows/${workflowStatus.run_id}/cancel`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Viewer-Role": viewerRole,
        },
        body: JSON.stringify({ reason: actionComments || "Cancelled by reviewer." }),
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Cancellation failed: HTTP ${res.status}`);
      }
      const data: WorkflowStatusResponse = await res.json();
      setWorkflowStatus(data);
      setModalMode(null);
      setActionComments("");
      setSuccessMessage("Workflow cancelled successfully.");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error cancelling workflow.";
      setErrorMessage(msg);
    } finally {
      setIsActionLoading(false);
    }
  };

  // Resume Workflow
  const handleResumeWorkflow = async () => {
    if (!workflowStatus) return;
    setIsActionLoading(true);
    setErrorMessage(null);
    try {
      const res = await fetch(`${backendBaseUrl}/api/v1/workflows/${workflowStatus.run_id}/resume`, {
        method: "POST",
        headers: { "X-Viewer-Role": viewerRole },
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Resume failed: HTTP ${res.status}`);
      }
      const data: WorkflowStatusResponse = await res.json();
      setWorkflowStatus(data);
      setSuccessMessage("Workflow resumed from latest persisted state.");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error resuming workflow.";
      setErrorMessage(msg);
    } finally {
      setIsActionLoading(false);
    }
  };

  // Helper badge color
  const getStatusBadge = (status: string) => {
    switch (status) {
      case "awaiting_approval":
        return "bg-amber-500/10 text-amber-300 border-amber-500/30";
      case "approved":
      case "completed":
        return "bg-emerald-500/10 text-emerald-300 border-emerald-500/30";
      case "revision_requested":
        return "bg-purple-500/10 text-purple-300 border-purple-500/30";
      case "running":
        return "bg-indigo-500/10 text-indigo-300 border-indigo-500/30 animate-pulse";
      case "cancelled":
        return "bg-slate-700/30 text-slate-400 border-slate-700";
      case "failed":
        return "bg-rose-500/10 text-rose-300 border-rose-500/30";
      default:
        return "bg-slate-800 text-slate-300 border-slate-700";
    }
  };

  const draft = workflowStatus?.draft_report;

  return (
    <div id="orchestration" className="mt-14 scroll-mt-20">
      <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-6 sm:p-8 backdrop-blur shadow-2xl relative overflow-hidden">
        {/* Ambient Gradient Glow */}
        <div className="pointer-events-none absolute -right-20 -top-20 h-64 w-64 rounded-full bg-purple-600/10 blur-3xl" />
        <div className="pointer-events-none absolute -left-20 -bottom-20 h-64 w-64 rounded-full bg-indigo-600/10 blur-3xl" />

        {/* Header & Badges */}
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 border-b border-slate-800 pb-6">
          <div>
            <div className="inline-flex items-center space-x-2 rounded-full border border-purple-500/30 bg-purple-500/10 px-3 py-1 text-xs font-medium text-purple-300">
              <span className="h-1.5 w-1.5 rounded-full bg-purple-400 animate-pulse" />
              <span>Phase 7 — LangGraph Multi-Agent Orchestration &amp; Human-in-the-Loop</span>
            </div>
            <h2 className="mt-2 text-2xl font-bold tracking-tight text-white sm:text-3xl">
              Multi-Agent Review Orchestration Engine
            </h2>
            <p className="mt-1 text-sm text-slate-400 max-w-2xl">
              Deterministic 4-agent state graph coordinating scoped evidence retrieval, feedback analysis, bias audits,
              and grounded draft synthesis with an immutable Human Approval decision pause.
            </p>
          </div>

          {/* Current Status Indicator */}
          {workflowStatus && (
            <div className="flex flex-col items-end">
              <span className="text-xs uppercase tracking-wider text-slate-400 font-semibold mb-1">
                Workflow State
              </span>
              <div className={`px-3 py-1.5 rounded-lg border text-sm font-semibold flex items-center gap-2 ${getStatusBadge(workflowStatus.workflow_status)}`}>
                <span className="capitalize">{workflowStatus.workflow_status.replace(/_/g, " ")}</span>
                {workflowStatus.workflow_status === "awaiting_approval" && (
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500"></span>
                  </span>
                )}
              </div>
              <span className="text-xs text-slate-500 mt-1 font-mono">
                Run: {workflowStatus.run_id.slice(0, 8)}...
              </span>
            </div>
          )}
        </div>

        {/* Notification alerts */}
        {errorMessage && (
          <div className="mt-4 rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-300 flex items-start gap-3">
            <svg className="w-5 h-5 flex-shrink-0 mt-0.5 text-rose-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div>
              <span className="font-semibold block">Execution Warning:</span>
              <span>{errorMessage}</span>
            </div>
          </div>
        )}
        {successMessage && (
          <div className="mt-4 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4 text-sm text-emerald-300 flex items-start gap-3">
            <svg className="w-5 h-5 flex-shrink-0 mt-0.5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            <div>{successMessage}</div>
          </div>
        )}

        {/* Controls Toolbar */}
        <div className="mt-6 grid grid-cols-1 md:grid-cols-12 gap-4 items-end bg-slate-950/50 p-4 rounded-xl border border-slate-800/80">
          <div className="md:col-span-5">
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Target Review Cycle
            </label>
            <select
              value={selectedCycleId}
              onChange={(e) => setSelectedCycleId(e.target.value)}
              disabled={isLoadingCycles || isRunning}
              className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500"
            >
              {cycles.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.title} ({c.status})
                </option>
              ))}
            </select>
          </div>

          <div className="md:col-span-3">
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Viewer Authorization Role
            </label>
            <select
              value={viewerRole}
              onChange={(e) => setViewerRole(e.target.value)}
              disabled={isRunning}
              className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500"
            >
              <option value="manager">Manager (Authorized Reviewer)</option>
              <option value="admin">Admin (System Lead)</option>
              <option value="employee">Employee (Subject)</option>
            </select>
          </div>

          <div className="md:col-span-4 flex gap-2">
            <button
              onClick={() => handleStartWorkflow(false)}
              disabled={isRunning || !selectedCycleId}
              className="flex-1 rounded-lg bg-gradient-to-r from-purple-600 via-indigo-600 to-indigo-700 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-purple-600/20 hover:from-purple-500 hover:to-indigo-600 disabled:opacity-50 transition flex items-center justify-center gap-2"
            >
              {isRunning ? (
                <>
                  <svg className="animate-spin h-4 w-4 text-white" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
                  </svg>
                  <span>Orchestrating...</span>
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span>Start Multi-Agent Analysis</span>
                </>
              )}
            </button>

            {workflowStatus && (
              <button
                onClick={() => handleStartWorkflow(true)}
                title="Force re-run new multi-agent cycle"
                disabled={isRunning}
                className="px-3 py-2 rounded-lg border border-slate-700 bg-slate-800 text-slate-300 hover:text-white hover:bg-slate-750 text-xs font-medium transition"
              >
                Re-Run
              </button>
            )}
          </div>
        </div>

        {/* 5-Stage Visual Workflow Graph */}
        <div className="mt-8">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300">
              LangGraph State Machine Pipeline
            </h3>
            <span className="text-xs text-slate-500 font-mono">
              Directed Graph: 4 Specialists &rarr; Decision Pause &rarr; Finalization
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
            {/* Stage 1: Evidence Retrieval */}
            <div className={`p-4 rounded-xl border ${workflowStatus?.stages?.find(s => s.stage_name === "evidence_retrieval")?.status === "completed" ? "border-emerald-500/40 bg-emerald-500/5" : "border-slate-800 bg-slate-950/60"}`}>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-slate-400">Node 1</span>
                <span className={`text-[10px] px-2 py-0.5 rounded font-mono font-bold ${workflowStatus?.stages?.find(s => s.stage_name === "evidence_retrieval")?.status === "completed" ? "bg-emerald-500/20 text-emerald-300" : "bg-slate-800 text-slate-400"}`}>
                  {workflowStatus?.stages?.find(s => s.stage_name === "evidence_retrieval")?.status || "idle"}
                </span>
              </div>
              <div className="text-sm font-bold text-white mb-1">EvidenceRetrieval</div>
              <p className="text-xs text-slate-400">Scoped document parsing &amp; gap identification.</p>
              {workflowStatus && (
                <div className="mt-2 text-[11px] text-slate-400 font-mono">
                  Items: <span className="text-indigo-400 font-bold">{String(workflowStatus.stages?.find(s => s.stage_name === "evidence_retrieval")?.summary_data?.evidence_count ?? "-")}</span>
                </div>
              )}
            </div>

            {/* Stage 2: Feedback Analysis */}
            <div className={`p-4 rounded-xl border ${workflowStatus?.stages?.find(s => s.stage_name === "feedback_analysis")?.status === "completed" ? "border-emerald-500/40 bg-emerald-500/5" : "border-slate-800 bg-slate-950/60"}`}>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-slate-400">Node 2</span>
                <span className={`text-[10px] px-2 py-0.5 rounded font-mono font-bold ${workflowStatus?.stages?.find(s => s.stage_name === "feedback_analysis")?.status === "completed" ? "bg-emerald-500/20 text-emerald-300" : "bg-slate-800 text-slate-400"}`}>
                  {workflowStatus?.stages?.find(s => s.stage_name === "feedback_analysis")?.status || "idle"}
                </span>
              </div>
              <div className="text-sm font-bold text-white mb-1">FeedbackAnalysis</div>
              <p className="text-xs text-slate-400">360° thematic synthesis &amp; atomic findings.</p>
              {workflowStatus && (
                <div className="mt-2 text-[11px] text-slate-400 font-mono">
                  Strengths: <span className="text-purple-400 font-bold">{String(workflowStatus.stages?.find(s => s.stage_name === "feedback_analysis")?.summary_data?.strengths_count ?? "-")}</span>
                </div>
              )}
            </div>

            {/* Stage 3: Bias Auditor */}
            <div className={`p-4 rounded-xl border ${workflowStatus?.stages?.find(s => s.stage_name === "bias_audit")?.status === "completed" ? "border-emerald-500/40 bg-emerald-500/5" : "border-slate-800 bg-slate-950/60"}`}>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-slate-400">Node 3</span>
                <span className={`text-[10px] px-2 py-0.5 rounded font-mono font-bold ${workflowStatus?.stages?.find(s => s.stage_name === "bias_audit")?.status === "completed" ? "bg-emerald-500/20 text-emerald-300" : "bg-slate-800 text-slate-400"}`}>
                  {workflowStatus?.stages?.find(s => s.stage_name === "bias_audit")?.status || "idle"}
                </span>
              </div>
              <div className="text-sm font-bold text-white mb-1">BiasAuditorAgent</div>
              <p className="text-xs text-slate-400">5 deterministic rules &amp; health score.</p>
              {workflowStatus && (
                <div className="mt-2 text-[11px] text-slate-400 font-mono">
                  Health: <span className="text-emerald-400 font-bold">{workflowStatus.audit_health_score !== undefined ? `${workflowStatus.audit_health_score.toFixed(1)}%` : "-"}</span>
                </div>
              )}
            </div>

            {/* Stage 4: Review Synthesis */}
            <div className={`p-4 rounded-xl border ${workflowStatus?.stages?.find(s => s.stage_name === "review_synthesis")?.status === "completed" ? "border-emerald-500/40 bg-emerald-500/5" : "border-slate-800 bg-slate-950/60"}`}>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-slate-400">Node 4</span>
                <span className={`text-[10px] px-2 py-0.5 rounded font-mono font-bold ${workflowStatus?.stages?.find(s => s.stage_name === "review_synthesis")?.status === "completed" ? "bg-emerald-500/20 text-emerald-300" : "bg-slate-800 text-slate-400"}`}>
                  {workflowStatus?.stages?.find(s => s.stage_name === "review_synthesis")?.status || "idle"}
                </span>
              </div>
              <div className="text-sm font-bold text-white mb-1">ReviewSynthesis</div>
              <p className="text-xs text-slate-400">Citations-grounded draft generation.</p>
              {workflowStatus && (
                <div className="mt-2 text-[11px] text-slate-400 font-mono">
                  Citations: <span className="text-cyan-400 font-bold">{draft?.citations?.length ?? "-"}</span>
                </div>
              )}
            </div>

            {/* Stage 5: Human Approval Pause Boundary */}
            <div className={`p-4 rounded-xl border relative ${
              workflowStatus?.workflow_status === "awaiting_approval"
                ? "border-amber-500/60 bg-amber-500/10 shadow-lg shadow-amber-500/10"
                : workflowStatus?.workflow_status === "completed" || workflowStatus?.workflow_status === "approved"
                ? "border-emerald-500/40 bg-emerald-500/5"
                : "border-slate-800 bg-slate-950/60"
            }`}>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-amber-400 flex items-center gap-1">
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                  </svg>
                  Boundary
                </span>
                <span className={`text-[10px] px-2 py-0.5 rounded font-mono font-bold ${
                  workflowStatus?.workflow_status === "awaiting_approval"
                    ? "bg-amber-500/20 text-amber-300 animate-pulse"
                    : workflowStatus?.workflow_status === "completed"
                    ? "bg-emerald-500/20 text-emerald-300"
                    : "bg-slate-800 text-slate-400"
                }`}>
                  {workflowStatus?.workflow_status === "awaiting_approval" ? "PAUSED" : (workflowStatus?.workflow_status || "idle")}
                </span>
              </div>
              <div className="text-sm font-bold text-white mb-1">HumanApprovalPause</div>
              <p className="text-xs text-slate-400">Mandatory human decision gate.</p>
              {workflowStatus?.approval_metadata?.decision && (
                <div className="mt-2 text-[11px] text-emerald-400 font-mono">
                  Decision: <span className="font-bold uppercase">{workflowStatus.approval_metadata.decision}</span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Human Decision Control Bar (When Paused at Approval Boundary) */}
        {workflowStatus && (
          <div className="mt-8 p-5 rounded-xl border border-amber-500/30 bg-amber-500/5 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 text-amber-300 font-bold text-sm">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
                <span>Human-in-the-Loop Governance Decision</span>
              </div>
              <p className="text-xs text-slate-400 mt-1 max-w-xl">
                {workflowStatus.workflow_status === "awaiting_approval"
                  ? "Multi-agent synthesis is paused awaiting authorized reviewer decision. Approve to finalize or request revisions with feedback."
                  : workflowStatus.workflow_status === "completed"
                  ? "This review cycle has been formally approved and finalized by an authorized manager."
                  : `Current status: ${workflowStatus.workflow_status.replace(/_/g, " ")}.`}
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              {workflowStatus.available_actions.includes("approve") && (
                <button
                  onClick={() => setModalMode("approve")}
                  disabled={isActionLoading}
                  className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs transition flex items-center gap-1.5 shadow-md shadow-emerald-600/20"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  <span>Approve &amp; Finalize</span>
                </button>
              )}

              {workflowStatus.available_actions.includes("request_revision") && (
                <button
                  onClick={() => setModalMode("revision")}
                  disabled={isActionLoading}
                  className="px-4 py-2 rounded-lg bg-purple-600/80 hover:bg-purple-500 text-white font-semibold text-xs transition flex items-center gap-1.5"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                  <span>Request Revision</span>
                </button>
              )}

              {workflowStatus.available_actions.includes("resume") && (
                <button
                  onClick={handleResumeWorkflow}
                  disabled={isActionLoading}
                  className="px-3 py-2 rounded-lg bg-indigo-600/80 hover:bg-indigo-500 text-white font-semibold text-xs transition flex items-center gap-1"
                >
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                  </svg>
                  <span>Resume</span>
                </button>
              )}

              {workflowStatus.available_actions.includes("cancel") && (
                <button
                  onClick={() => setModalMode("cancel")}
                  disabled={isActionLoading}
                  className="px-3 py-2 rounded-lg border border-slate-700 bg-slate-800 text-slate-300 hover:text-white hover:bg-slate-750 text-xs font-semibold transition"
                >
                  Cancel
                </button>
              )}
            </div>
          </div>
        )}

        {/* Synthesized Draft Review Inspection Interface */}
        {draft ? (
          <div className="mt-8 border-t border-slate-800 pt-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
              <div>
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <span>Synthesized Performance Review Report</span>
                  <span className="text-xs px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 font-mono">
                    v{draft.version_number} &bull; {draft.status}
                  </span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Grounded across {draft.citations?.length || 0} verified evidence artifacts with deterministic bias audit checks.
                </p>
              </div>

              {/* Navigation Tabs */}
              <div className="flex flex-wrap gap-1 bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs">
                <button
                  onClick={() => setActiveTab("summary")}
                  className={`px-3 py-1.5 rounded-md font-medium transition ${activeTab === "summary" ? "bg-purple-600 text-white" : "text-slate-400 hover:text-white"}`}
                >
                  Executive Summary
                </button>
                <button
                  onClick={() => setActiveTab("strengths")}
                  className={`px-3 py-1.5 rounded-md font-medium transition ${activeTab === "strengths" ? "bg-purple-600 text-white" : "text-slate-400 hover:text-white"}`}
                >
                  Strengths ({draft.strengths?.length || 0})
                </button>
                <button
                  onClick={() => setActiveTab("growth")}
                  className={`px-3 py-1.5 rounded-md font-medium transition ${activeTab === "growth" ? "bg-purple-600 text-white" : "text-slate-400 hover:text-white"}`}
                >
                  Growth Areas ({draft.growth_areas?.length || 0})
                </button>
                <button
                  onClick={() => setActiveTab("goals")}
                  className={`px-3 py-1.5 rounded-md font-medium transition ${activeTab === "goals" ? "bg-purple-600 text-white" : "text-slate-400 hover:text-white"}`}
                >
                  Goals ({draft.goal_progress?.length || 0})
                </button>
                <button
                  onClick={() => setActiveTab("audit")}
                  className={`px-3 py-1.5 rounded-md font-medium transition ${activeTab === "audit" ? "bg-purple-600 text-white" : "text-slate-400 hover:text-white"}`}
                >
                  Audit ({draft.bias_audit_summary?.total_flags || 0} flags)
                </button>
                <button
                  onClick={() => setActiveTab("questions")}
                  className={`px-3 py-1.5 rounded-md font-medium transition ${activeTab === "questions" ? "bg-purple-600 text-white" : "text-slate-400 hover:text-white"}`}
                >
                  Sync Questions ({draft.suggested_discussion_questions?.length || 0})
                </button>
              </div>
            </div>

            {/* Tab 1: Executive Summary */}
            {activeTab === "summary" && (
              <div className="space-y-4">
                <div className="p-5 rounded-xl bg-slate-950/70 border border-slate-800">
                  <h4 className="text-xs uppercase font-semibold text-purple-300 tracking-wider mb-2">
                    Executive Summary Statement
                  </h4>
                  <p className="text-sm text-slate-200 leading-relaxed font-sans">
                    {draft.executive_summary}
                  </p>
                </div>

                {/* Evidence Gaps and Limitations */}
                {draft.evidence_gaps_and_limitations?.length > 0 && (
                  <div className="p-4 rounded-xl bg-slate-950/40 border border-slate-800">
                    <h4 className="text-xs uppercase font-semibold text-slate-400 tracking-wider mb-2">
                      Report Limitations &amp; Identified Gaps
                    </h4>
                    <ul className="list-disc list-inside text-xs text-slate-300 space-y-1">
                      {draft.evidence_gaps_and_limitations.map((gap, i) => (
                        <li key={i}>{gap}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            {/* Tab 2: Strengths */}
            {activeTab === "strengths" && (
              <div className="space-y-3">
                {draft.strengths?.length === 0 ? (
                  <p className="text-xs text-slate-400 italic">No specific strengths extracted.</p>
                ) : (
                  draft.strengths.map((s, idx) => (
                    <div key={idx} className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-sm font-bold text-white">{s.title}</span>
                        {s.confidence && (
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                            Confidence: {s.confidence}
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-slate-300 leading-relaxed mb-3">{s.description}</p>
                      {s.supporting_evidence_ids && s.supporting_evidence_ids.length > 0 && (
                        <div className="flex flex-wrap items-center gap-1.5 pt-2 border-t border-slate-800/80">
                          <span className="text-[10px] text-slate-500 font-semibold uppercase">Verified Citations:</span>
                          {s.supporting_evidence_ids.map((cid, cidx) => (
                            <span key={cidx} className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800/50">
                              {cid.slice(0, 8)}...
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            )}

            {/* Tab 3: Growth Areas */}
            {activeTab === "growth" && (
              <div className="space-y-3">
                {draft.growth_areas?.length === 0 ? (
                  <p className="text-xs text-slate-400 italic">No development opportunities identified.</p>
                ) : (
                  draft.growth_areas.map((g, idx) => (
                    <div key={idx} className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
                      <div className="text-sm font-bold text-amber-300 mb-1">{g.title || "Growth Opportunity"}</div>
                      <p className="text-xs text-slate-300 leading-relaxed mb-2">{g.gap_observed}</p>
                      {g.development_suggestion && (
                        <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-300">
                          <span className="font-semibold text-purple-300">Recommendation: </span>
                          {g.development_suggestion}
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            )}

            {/* Tab 4: Goals Progress */}
            {activeTab === "goals" && (
              <div className="space-y-3">
                {draft.goal_progress?.length === 0 ? (
                  <p className="text-xs text-slate-400 italic">No cycle goals recorded.</p>
                ) : (
                  draft.goal_progress.map((g, idx) => (
                    <div key={idx} className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 flex items-start justify-between gap-4">
                      <div>
                        <div className="text-sm font-semibold text-white mb-1">{g.description}</div>
                        {g.outcome_notes && (
                          <p className="text-xs text-slate-400">{g.outcome_notes}</p>
                        )}
                      </div>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-800 capitalize">
                        {g.status}
                      </span>
                    </div>
                  ))
                )}
              </div>
            )}

            {/* Tab 5: Bias Audit */}
            {activeTab === "audit" && (
              <div className="p-5 rounded-xl bg-slate-950/60 border border-slate-800 space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="text-sm font-bold text-white">Deterministic Bias Audit Validation</h4>
                    <p className="text-xs text-slate-400">All 5 deterministic rules evaluated before synthesis.</p>
                  </div>
                  <div className="text-right">
                    <span className="text-2xl font-extrabold text-emerald-400 font-mono">
                      {draft.bias_audit_summary?.health_score?.toFixed(1) ?? "100.0"}%
                    </span>
                    <span className="block text-[10px] text-slate-400 uppercase font-semibold">Audit Health Score</span>
                  </div>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-slate-800">
                  <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800 text-center">
                    <span className="text-xs text-slate-400 block">Total Flags</span>
                    <span className="text-base font-bold text-white font-mono">{draft.bias_audit_summary?.total_flags ?? 0}</span>
                  </div>
                  <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800 text-center">
                    <span className="text-xs text-slate-400 block">Review Ready</span>
                    <span className={`text-base font-bold font-mono ${draft.bias_audit_summary?.is_ready_for_review ? "text-emerald-400" : "text-amber-400"}`}>
                      {draft.bias_audit_summary?.is_ready_for_review ? "Yes" : "Caution"}
                    </span>
                  </div>
                  <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800 text-center col-span-2">
                    <span className="text-xs text-slate-400 block">Grounding Guarantee</span>
                    <span className="text-xs font-semibold text-indigo-400">Zero Unverified Citations</span>
                  </div>
                </div>
              </div>
            )}

            {/* Tab 6: Discussion Questions */}
            {activeTab === "questions" && (
              <div className="space-y-3">
                {draft.suggested_discussion_questions?.length === 0 ? (
                  <p className="text-xs text-slate-400 italic">No discussion questions generated.</p>
                ) : (
                  draft.suggested_discussion_questions.map((q, idx) => {
                    const isObj = typeof q === "object" && q !== null;
                    const questionText = isObj ? q.question : q;
                    const category = isObj ? q.category : "Sync Theme";
                    const context = isObj ? q.context : undefined;

                    return (
                      <div key={idx} className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-purple-950 text-purple-300 border border-purple-800 uppercase font-semibold">
                          {category}
                        </span>
                        <p className="text-sm font-medium text-white mt-2">{questionText}</p>
                        {context && <p className="text-xs text-slate-400 mt-1">{context}</p>}
                      </div>
                    );
                  })
                )}
              </div>
            )}
          </div>
        ) : (
          !isRunning && (
            <div className="mt-8 text-center p-8 rounded-xl border border-dashed border-slate-800 bg-slate-950/30">
              <svg className="w-10 h-10 text-slate-600 mx-auto mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
              <p className="text-sm font-semibold text-slate-300">No active multi-agent run for this cycle</p>
              <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                Click &quot;Start Multi-Agent Analysis&quot; above to initiate the LangGraph orchestration pipeline.
              </p>
            </div>
          )
        )}

        {/* Modal for Decision Actions */}
        {modalMode && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-sm">
            <div className="w-full max-w-lg rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-2xl">
              <h3 className="text-lg font-bold text-white mb-2">
                {modalMode === "approve"
                  ? "Approve & Finalize Performance Review"
                  : modalMode === "revision"
                  ? "Request Review Revisions"
                  : "Cancel Multi-Agent Workflow"}
              </h3>
              <p className="text-xs text-slate-400 mb-4">
                {modalMode === "approve"
                  ? "This records formal manager approval, transitions report status to approved, and logs an immutable audit event."
                  : modalMode === "revision"
                  ? "Specify precise feedback, missing context, or benchmark results required before final approval."
                  : "Cancels the active workflow. State is marked cancelled."}
              </p>

              <div className="mb-4">
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  {modalMode === "revision" ? "Revision Instructions (Required)" : "Manager Comments (Optional)"}
                </label>
                <textarea
                  rows={4}
                  value={actionComments}
                  onChange={(e) => setActionComments(e.target.value)}
                  placeholder={
                    modalMode === "approve"
                      ? "e.g., Outstanding contributions. Review approved without objections."
                      : modalMode === "revision"
                      ? "e.g., Please provide benchmarking evidence for the consensus algorithm."
                      : "Reason for cancellation..."
                  }
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 p-3 text-xs text-white focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500"
                />
              </div>

              <div className="flex justify-end gap-2">
                <button
                  onClick={() => {
                    setModalMode(null);
                    setActionComments("");
                  }}
                  disabled={isActionLoading}
                  className="px-4 py-2 rounded-lg border border-slate-700 bg-slate-800 text-slate-300 hover:text-white text-xs font-semibold"
                >
                  Close
                </button>
                <button
                  onClick={() => {
                    if (modalMode === "approve") handleApprove();
                    else if (modalMode === "revision") handleRequestRevision();
                    else if (modalMode === "cancel") handleCancelWorkflow();
                  }}
                  disabled={isActionLoading || (modalMode === "revision" && !actionComments.trim())}
                  className={`px-4 py-2 rounded-lg text-white text-xs font-semibold transition ${
                    modalMode === "approve"
                      ? "bg-emerald-600 hover:bg-emerald-500"
                      : modalMode === "revision"
                      ? "bg-purple-600 hover:bg-purple-500"
                      : "bg-rose-600 hover:bg-rose-500"
                  } disabled:opacity-50`}
                >
                  {isActionLoading ? "Submitting..." : "Confirm Decision"}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
