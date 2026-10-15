"use client";

import React, { useCallback, useEffect, useState } from "react";

interface ReportSectionStrength {
  theme?: string;
  narrative?: string;
  supporting_evidence_ids?: string[];
  confidence_score?: number;
  title?: string;
  description?: string;
}

interface ReportSectionGrowthArea {
  theme?: string;
  title?: string;
  narrative?: string;
  gap_observed?: string;
  development_suggestion?: string;
  supporting_evidence_ids?: string[];
  confidence_score?: number;
}

interface StructuredContent {
  executive_summary?: string;
  strengths?: ReportSectionStrength[];
  growth_areas?: ReportSectionGrowthArea[];
  goal_progress?: Array<{
    id?: string;
    description?: string;
    status?: string;
    outcome_notes?: string;
  }>;
  impact_highlights?: Array<{
    title?: string;
    impact_summary?: string;
    citations?: string[];
  }>;
  evidence_gaps_and_limitations?: string[];
  suggested_discussion_questions?: Array<string | { category?: string; question?: string }>;
  reviewer_notes?: string;
  citations?: string[];
  [key: string]: unknown;
}

interface ReportDetail {
  id: string;
  cycle_id: string;
  version_number: number;
  status: "draft" | "revision_requested" | "approved";
  structured_content: StructuredContent;
  is_approved: boolean;
  approval_count: number;
  latest_approval?: {
    id: string;
    reviewer_name?: string;
    reviewer_role?: string;
    decision: string;
    version_number?: number;
    comments?: string;
    created_at: string;
  };
  created_at: string;
  updated_at: string;
}

interface VersionSummary {
  version_id: string;
  report_id: string;
  cycle_id: string;
  version_number: number;
  status: string;
  changed_section: string;
  change_summary?: string;
  author_id?: string;
  author_role?: string;
  is_ai_generated: boolean;
  created_at: string;
}

interface SectionDiff {
  section_key: string;
  is_modified: boolean;
  diff_type: string;
  previous_value?: unknown;
  current_value?: unknown;
  unified_diff?: string;
  added_items?: unknown[];
  removed_items?: unknown[];
}

interface VersionComparison {
  report_id: string;
  from_version_number: number;
  to_version_number: number;
  sections_changed: string[];
  section_diffs: Record<string, SectionDiff>;
  status_changed: boolean;
  from_status: string;
  to_status: string;
  change_summary: string[];
}

interface AuditRecord {
  id: string;
  action: string;
  resource_type: string;
  resource_id: string;
  actor_id?: string;
  actor_name?: string;
  actor_role?: string;
  metadata_json: Record<string, unknown>;
  created_at: string;
}

interface ReviewCycleOption {
  id: string;
  title: string;
  employee_id: string;
  status: string;
}

export function ReportGovernanceCard() {
  const [cycles, setCycles] = useState<ReviewCycleOption[]>([]);
  const [selectedCycleId, setSelectedCycleId] = useState<string>("");
  const [viewerRole, setViewerRole] = useState<string>("manager");
  const [report, setReport] = useState<ReportDetail | null>(null);
  const [versions, setVersions] = useState<VersionSummary[]>([]);
  const [auditEvents, setAuditEvents] = useState<AuditRecord[]>([]);

  // Navigation tab
  const [activeTab, setActiveTab] = useState<"editor" | "versions" | "compare" | "audit">("editor");

  // State loading/feedback
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isActionLoading, setIsActionLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Section Editing state
  const [editingSection, setEditingSection] = useState<string | null>(null);
  const [sectionContent, setSectionContent] = useState<string>("");
  const [sectionReason, setSectionReason] = useState<string>("");

  // Version Comparison state
  const [fromVersionNumber, setFromVersionNumber] = useState<string>("");
  const [toVersionNumber, setToVersionNumber] = useState<string>("");
  const [comparisonResult, setComparisonResult] = useState<VersionComparison | null>(null);
  const [isComparing, setIsComparing] = useState<boolean>(false);

  // Historical Version Inspection Modal
  const [inspectedVersion, setInspectedVersion] = useState<VersionSummary | null>(null);
  const [inspectedContent, setInspectedContent] = useState<StructuredContent | null>(null);
  const [isLoadingSnapshot, setIsLoadingSnapshot] = useState<boolean>(false);

  // Approval / Revision dialog state
  const [approvalModalMode, setApprovalModalMode] = useState<"approve" | "revision" | null>(null);
  const [approvalComments, setApprovalComments] = useState<string>("");

  const rawApiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const backendBaseUrl = rawApiUrl.replace(/\/api\/v1\/?$/, "").replace(/\/+$/, "");

  // 1. Fetch Review Cycles on mount
  useEffect(() => {
    let ignore = false;
    async function fetchCycles() {
      try {
        const res = await fetch(`${backendBaseUrl}/api/v1/review-cycles?limit=20`, { cache: "no-store" });
        if (res.ok && !ignore) {
          const data: ReviewCycleOption[] = await res.json();
          setCycles(data);
          if (data.length > 0) {
            setSelectedCycleId((prev) => prev || data[0].id);
          }
        }
      } catch (err) {
        console.warn("Could not load review cycles:", err);
      } finally {
        if (!ignore) {
          setIsLoading(false);
        }
      }
    }
    fetchCycles();
    return () => {
      ignore = true;
    };
  }, [backendBaseUrl]);

  // 2. Fetch Report when cycle or viewerRole changes
  useEffect(() => {
    if (!selectedCycleId) return;
    let ignore = false;

    async function fetchReport() {
      try {
        const res = await fetch(`${backendBaseUrl}/api/v1/review-cycles/${selectedCycleId}/report`, {
          headers: { "X-Viewer-Role": viewerRole },
          cache: "no-store",
        });

        if (!res.ok) {
          if (res.status === 404 && !ignore) {
            setReport(null);
            setVersions([]);
            setAuditEvents([]);
            return;
          }
          const err = await res.json().catch(() => ({}));
          throw new Error(err.detail || `Failed to fetch report (HTTP ${res.status})`);
        }

        const repData: ReportDetail = await res.json();
        if (ignore) return;
        setReport(repData);

        const [vRes, aRes] = await Promise.all([
          fetch(`${backendBaseUrl}/api/v1/reports/${repData.id}/versions`, {
            headers: { "X-Viewer-Role": viewerRole },
            cache: "no-store",
          }),
          fetch(`${backendBaseUrl}/api/v1/reports/${repData.id}/audit-events`, {
            headers: { "X-Viewer-Role": viewerRole },
            cache: "no-store",
          }),
        ]);

        if (ignore) return;

        if (vRes.ok) {
          const vData = await vRes.json();
          setVersions(vData.versions || []);
          if (vData.versions?.length >= 2) {
            setFromVersionNumber(String(vData.versions[vData.versions.length - 1].version_number));
            setToVersionNumber(String(vData.versions[0].version_number));
          } else if (vData.versions?.length === 1) {
            setFromVersionNumber("1");
            setToVersionNumber("1");
          }
        }

        if (aRes.ok) {
          const aData = await aRes.json();
          setAuditEvents(aData.events || []);
        }
      } catch (err: unknown) {
        if (!ignore) {
          setErrorMessage(err instanceof Error ? err.message : "Failed to load report data.");
        }
      }
    }

    fetchReport();
    return () => {
      ignore = true;
    };
  }, [selectedCycleId, viewerRole, backendBaseUrl]);

  // Manual or post-action reload helper
  const loadReportData = useCallback(async () => {
    if (!selectedCycleId) return;
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const res = await fetch(`${backendBaseUrl}/api/v1/review-cycles/${selectedCycleId}/report`, {
        headers: { "X-Viewer-Role": viewerRole },
        cache: "no-store",
      });

      if (!res.ok) {
        if (res.status === 404) {
          setReport(null);
          setVersions([]);
          setAuditEvents([]);
          return;
        }
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Failed to fetch report (HTTP ${res.status})`);
      }

      const repData: ReportDetail = await res.json();
      setReport(repData);

      const [vRes, aRes] = await Promise.all([
        fetch(`${backendBaseUrl}/api/v1/reports/${repData.id}/versions`, {
          headers: { "X-Viewer-Role": viewerRole },
          cache: "no-store",
        }),
        fetch(`${backendBaseUrl}/api/v1/reports/${repData.id}/audit-events`, {
          headers: { "X-Viewer-Role": viewerRole },
          cache: "no-store",
        }),
      ]);

      if (vRes.ok) {
        const vData = await vRes.json();
        setVersions(vData.versions || []);
        if (vData.versions?.length >= 2) {
          setFromVersionNumber(String(vData.versions[vData.versions.length - 1].version_number));
          setToVersionNumber(String(vData.versions[0].version_number));
        } else if (vData.versions?.length === 1) {
          setFromVersionNumber("1");
          setToVersionNumber("1");
        }
      }

      if (aRes.ok) {
        const aData = await aRes.json();
        setAuditEvents(aData.events || []);
      }
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Failed to load report data.");
    } finally {
      setIsLoading(false);
    }
  }, [backendBaseUrl, selectedCycleId, viewerRole]);

  // 3. Section Editing Handlers
  const handleStartEdit = (sectionKey: string, currentVal: unknown) => {
    setEditingSection(sectionKey);
    setSectionReason("");
    if (typeof currentVal === "string") {
      setSectionContent(currentVal);
    } else {
      setSectionContent(JSON.stringify(currentVal, null, 2));
    }
  };

  const handleSaveSection = async () => {
    if (!report || !editingSection) return;
    setIsActionLoading(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    let parsedContent: unknown = sectionContent;
    if (editingSection === "strengths" || editingSection === "growth_areas") {
      try {
        parsedContent = JSON.parse(sectionContent);
      } catch {
        setErrorMessage("Section content must be valid JSON array of objects.");
        setIsActionLoading(false);
        return;
      }
    }

    try {
      const res = await fetch(`${backendBaseUrl}/api/v1/reports/${report.id}/sections/${editingSection}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Viewer-Role": viewerRole,
        },
        body: JSON.stringify({
          content: parsedContent,
          reason: sectionReason.trim() || undefined,
          base_version_number: report.version_number,
        }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `HTTP ${res.status}: Failed to update section.`);
      }

      const updatedReport: ReportDetail = await res.json();
      setReport(updatedReport);
      setEditingSection(null);
      setSuccessMessage(
        `Section '${editingSection}' saved successfully. Advanced to version ${updatedReport.version_number}.`
      );
      await loadReportData();
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Failed to save section.");
    } finally {
      setIsActionLoading(false);
    }
  };

  // 4. Version Comparison Handler
  const handleCompareVersions = async () => {
    if (!report || !fromVersionNumber || !toVersionNumber) return;
    setIsComparing(true);
    setErrorMessage(null);
    try {
      const res = await fetch(
        `${backendBaseUrl}/api/v1/reports/${report.id}/compare?from_version=${fromVersionNumber}&to_version=${toVersionNumber}`,
        {
          headers: { "X-Viewer-Role": viewerRole },
          cache: "no-store",
        }
      );
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to compare versions.");
      }
      const diffData: VersionComparison = await res.json();
      setComparisonResult(diffData);
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Version comparison failed.");
    } finally {
      setIsComparing(false);
    }
  };

  // 5. Inspect Historical Snapshot
  const handleInspectSnapshot = async (ver: VersionSummary) => {
    if (!report) return;
    setInspectedVersion(ver);
    setIsLoadingSnapshot(true);
    try {
      const res = await fetch(`${backendBaseUrl}/api/v1/reports/${report.id}/versions/${ver.version_number}`, {
        headers: { "X-Viewer-Role": viewerRole },
        cache: "no-store",
      });
      if (res.ok) {
        const data = await res.json();
        setInspectedContent(data.structured_content);
      }
    } catch (err) {
      console.warn("Could not load snapshot detail:", err);
    } finally {
      setIsLoadingSnapshot(false);
    }
  };

  // 6. Approval / Revision Handlers
  const handleApproveReport = async () => {
    if (!report) return;
    setIsActionLoading(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      const res = await fetch(`${backendBaseUrl}/api/v1/reports/${report.id}/approve`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Viewer-Role": viewerRole,
        },
        body: JSON.stringify({
          version_number: report.version_number,
          comments: approvalComments.trim() || undefined,
        }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `HTTP ${res.status}: Approval failed.`);
      }

      const updated: ReportDetail = await res.json();
      setReport(updated);
      setApprovalModalMode(null);
      setApprovalComments("");
      setSuccessMessage(`Report Version ${updated.version_number} approved and finalized! Immutable snapshot recorded.`);
      await loadReportData();
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Approval submission failed.");
    } finally {
      setIsActionLoading(false);
    }
  };

  const handleRequestRevision = async () => {
    if (!report) return;
    if (!approvalComments.trim()) {
      setErrorMessage("Revision instructions and comments are mandatory.");
      return;
    }
    setIsActionLoading(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      const res = await fetch(`${backendBaseUrl}/api/v1/reports/${report.id}/request-revision`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Viewer-Role": viewerRole,
        },
        body: JSON.stringify({
          comments: approvalComments.trim(),
        }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `HTTP ${res.status}: Revision request failed.`);
      }

      const updated: ReportDetail = await res.json();
      setReport(updated);
      setApprovalModalMode(null);
      setApprovalComments("");
      setSuccessMessage(`Revisions requested for Report Version ${updated.version_number}.`);
      await loadReportData();
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Revision request failed.");
    } finally {
      setIsActionLoading(false);
    }
  };

  return (
    <section id="governance" className="mt-14">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center space-x-2">
            <span className="inline-flex items-center rounded-md bg-purple-500/10 px-2.5 py-1 text-xs font-semibold text-purple-400 border border-purple-500/20">
              Phase 8 Feature
            </span>
            <span className="text-xs text-slate-400 font-mono">FR-11 · FR-12 · FR-13</span>
          </div>
          <h2 className="mt-2 text-2xl font-bold tracking-tight text-white sm:text-3xl">
            Human Approval, Versioning &amp; Governance
          </h2>
          <p className="mt-1 text-sm text-slate-400 max-w-2xl">
            Section-level draft editing with optimistic concurrency control, immutable version snapshots, deterministic diff comparison, and human manager sign-off.
          </p>
        </div>

        {/* Global Controls: Cycle Selector & Role Switcher */}
        <div className="mt-4 sm:mt-0 flex flex-wrap items-center gap-3">
          <div className="flex flex-col">
            <label className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Review Cycle</label>
            <select
              value={selectedCycleId}
              onChange={(e) => setSelectedCycleId(e.target.value)}
              className="mt-1 rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              disabled={isLoading || cycles.length === 0}
            >
              {cycles.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.title}
                </option>
              ))}
            </select>
          </div>

          <div className="flex flex-col">
            <label className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Viewer Role</label>
            <select
              value={viewerRole}
              onChange={(e) => setViewerRole(e.target.value)}
              className="mt-1 rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            >
              <option value="manager">Manager (Authorized)</option>
              <option value="administrator">Administrator (Full Access)</option>
              <option value="employee">Employee (Restricted / Read-Only)</option>
            </select>
          </div>

          <button
            onClick={loadReportData}
            disabled={isLoading}
            className="self-end rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-1.5 text-xs font-medium text-slate-300 hover:bg-slate-700 transition"
          >
            {isLoading ? "Refreshing..." : "↻ Refresh"}
          </button>
        </div>
      </div>

      {/* Notifications */}
      {errorMessage && (
        <div className="mt-4 rounded-xl border border-red-500/30 bg-red-950/40 p-4 text-sm text-red-200 flex items-start justify-between">
          <div>
            <span className="font-semibold text-red-400">Notice: </span>
            {errorMessage}
          </div>
          <button onClick={() => setErrorMessage(null)} className="text-red-400 hover:text-red-200 ml-4 font-bold">
            ✕
          </button>
        </div>
      )}

      {successMessage && (
        <div className="mt-4 rounded-xl border border-emerald-500/30 bg-emerald-950/40 p-4 text-sm text-emerald-200 flex items-start justify-between">
          <div>
            <span className="font-semibold text-emerald-400">Success: </span>
            {successMessage}
          </div>
          <button onClick={() => setSuccessMessage(null)} className="text-emerald-400 hover:text-emerald-200 ml-4 font-bold">
            ✕
          </button>
        </div>
      )}

      {/* Report Status Banner (when report exists) */}
      {report && (
        <div className="mt-6 flex flex-wrap items-center justify-between gap-4 rounded-xl border border-slate-800 bg-slate-900/60 p-4 backdrop-blur-md">
          <div className="flex items-center space-x-3">
            <span className="inline-flex items-center rounded-lg bg-indigo-500/20 px-2.5 py-1 text-sm font-bold text-indigo-300 border border-indigo-500/30">
              v{report.version_number}
            </span>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-sm font-semibold text-white">Active Report Status:</span>
                <span
                  className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wider ${
                    report.status === "approved"
                      ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                      : report.status === "revision_requested"
                      ? "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                      : "bg-cyan-500/20 text-cyan-400 border border-cyan-500/30"
                  }`}
                >
                  {report.status.replace("_", " ")}
                </span>
                {report.status === "approved" && (
                  <span className="text-xs text-emerald-400 font-medium">✓ Immutable Sign-off Protected</span>
                )}
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Last modified: {new Date(report.updated_at).toLocaleString()} · Total recorded versions: {versions.length}
              </p>
            </div>
          </div>

          {/* Action Buttons for Managers */}
          <div className="flex items-center space-x-2">
            {viewerRole !== "employee" && report.status !== "approved" && (
              <>
                <button
                  onClick={() => setApprovalModalMode("revision")}
                  disabled={isActionLoading}
                  className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-3.5 py-2 text-xs font-semibold text-amber-300 hover:bg-amber-500/20 transition"
                >
                  Request Revisions
                </button>
                <button
                  onClick={() => setApprovalModalMode("approve")}
                  disabled={isActionLoading}
                  className="rounded-lg border border-emerald-500/50 bg-emerald-600 px-4 py-2 text-xs font-bold text-white hover:bg-emerald-500 transition shadow-lg shadow-emerald-900/30"
                >
                  Approve Version {report.version_number}
                </button>
              </>
            )}
            {report.status === "approved" && (
              <span className="inline-flex items-center rounded-lg bg-emerald-950/60 border border-emerald-500/40 px-3 py-1.5 text-xs font-semibold text-emerald-300">
                ✓ Version {report.version_number} Finalized
              </span>
            )}
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="mt-6 flex border-b border-slate-800">
        <button
          onClick={() => setActiveTab("editor")}
          className={`px-4 py-2.5 text-xs font-semibold border-b-2 transition ${
            activeTab === "editor"
              ? "border-indigo-400 text-indigo-300"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          Draft Report &amp; Section Editor
        </button>
        <button
          onClick={() => setActiveTab("versions")}
          className={`px-4 py-2.5 text-xs font-semibold border-b-2 transition ${
            activeTab === "versions"
              ? "border-indigo-400 text-indigo-300"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          Version History ({versions.length})
        </button>
        <button
          onClick={() => setActiveTab("compare")}
          className={`px-4 py-2.5 text-xs font-semibold border-b-2 transition ${
            activeTab === "compare"
              ? "border-indigo-400 text-indigo-300"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          Deterministic Version Diff
        </button>
        <button
          onClick={() => setActiveTab("audit")}
          className={`px-4 py-2.5 text-xs font-semibold border-b-2 transition ${
            activeTab === "audit"
              ? "border-indigo-400 text-indigo-300"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          Governance Audit Trail ({auditEvents.length})
        </button>
      </div>

      {/* Main Content Area */}
      <div className="mt-6">
        {!report && !isLoading && (
          <div className="rounded-2xl border border-dashed border-slate-800 bg-slate-900/30 p-12 text-center">
            <h3 className="text-base font-semibold text-slate-300">No report draft generated yet</h3>
            <p className="mt-1 text-xs text-slate-500 max-w-md mx-auto">
              Run the Multi-Agent Review Workflow above to synthesize evidence, check bias, and produce an initial report draft for this cycle.
            </p>
          </div>
        )}

        {/* ---------------- Tab 1: Section-Level Editor ---------------- */}
        {report && activeTab === "editor" && (
          <div className="space-y-6">
            {/* Executive Summary Card */}
            <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5 backdrop-blur-md">
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <div className="flex items-center space-x-2">
                  <span className="h-2 w-2 rounded-full bg-cyan-400"></span>
                  <h3 className="text-sm font-bold text-white">Executive Summary</h3>
                </div>
                {viewerRole !== "employee" && editingSection !== "executive_summary" && (
                  <button
                    onClick={() => handleStartEdit("executive_summary", report.structured_content.executive_summary || "")}
                    className="rounded-md border border-slate-700 bg-slate-800 px-2.5 py-1 text-xs font-medium text-slate-300 hover:bg-slate-700 transition"
                  >
                    ✎ Edit Section
                  </button>
                )}
              </div>

              {editingSection === "executive_summary" ? (
                <div className="mt-4 space-y-3">
                  <textarea
                    rows={4}
                    value={sectionContent}
                    onChange={(e) => setSectionContent(e.target.value)}
                    className="w-full rounded-lg border border-slate-700 bg-slate-950 p-3 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
                    placeholder="Enter revised executive summary..."
                  />
                  <div>
                    <label className="text-[10px] uppercase font-bold text-slate-400">Reason for Change (Audit Tracked)</label>
                    <input
                      type="text"
                      value={sectionReason}
                      onChange={(e) => setSectionReason(e.target.value)}
                      placeholder="e.g. Clarified scope after one-on-one review meeting"
                      className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
                    />
                  </div>
                  <div className="flex justify-end space-x-2">
                    <button
                      onClick={() => setEditingSection(null)}
                      className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-700"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleSaveSection}
                      disabled={isActionLoading}
                      className="rounded-lg bg-indigo-600 px-4 py-1.5 text-xs font-bold text-white hover:bg-indigo-500 transition"
                    >
                      {isActionLoading ? "Saving Snapshot..." : "Save New Version"}
                    </button>
                  </div>
                </div>
              ) : (
                <p className="mt-3 text-xs leading-relaxed text-slate-300 whitespace-pre-wrap">
                  {report.structured_content.executive_summary || "No executive summary provided."}
                </p>
              )}
            </div>

            {/* Strengths Card */}
            <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5 backdrop-blur-md">
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <div className="flex items-center space-x-2">
                  <span className="h-2 w-2 rounded-full bg-emerald-400"></span>
                  <h3 className="text-sm font-bold text-white">
                    Validated Strengths ({report.structured_content.strengths?.length || 0})
                  </h3>
                </div>
                {viewerRole !== "employee" && editingSection !== "strengths" && (
                  <button
                    onClick={() => handleStartEdit("strengths", report.structured_content.strengths || [])}
                    className="rounded-md border border-slate-700 bg-slate-800 px-2.5 py-1 text-xs font-medium text-slate-300 hover:bg-slate-700 transition"
                  >
                    ✎ Edit Structured JSON
                  </button>
                )}
              </div>

              {editingSection === "strengths" ? (
                <div className="mt-4 space-y-3">
                  <textarea
                    rows={6}
                    value={sectionContent}
                    onChange={(e) => setSectionContent(e.target.value)}
                    className="w-full font-mono rounded-lg border border-slate-700 bg-slate-950 p-3 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
                  />
                  <div>
                    <label className="text-[10px] uppercase font-bold text-slate-400">Reason for Change</label>
                    <input
                      type="text"
                      value={sectionReason}
                      onChange={(e) => setSectionReason(e.target.value)}
                      placeholder="e.g. Added supporting citations from architectural RFC"
                      className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
                    />
                  </div>
                  <div className="flex justify-end space-x-2">
                    <button
                      onClick={() => setEditingSection(null)}
                      className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-700"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleSaveSection}
                      disabled={isActionLoading}
                      className="rounded-lg bg-indigo-600 px-4 py-1.5 text-xs font-bold text-white hover:bg-indigo-500 transition"
                    >
                      {isActionLoading ? "Saving Snapshot..." : "Save New Version"}
                    </button>
                  </div>
                </div>
              ) : (
                <div className="mt-3 space-y-3">
                  {(report.structured_content.strengths || []).map((s, idx) => (
                    <div key={idx} className="rounded-lg border border-slate-800/80 bg-slate-950/50 p-3">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-emerald-300">{s.theme || s.title || "Strength"}</span>
                        {s.confidence_score !== undefined && (
                          <span className="text-[10px] text-slate-400">
                            Confidence: {Math.round(s.confidence_score * 100)}%
                          </span>
                        )}
                      </div>
                      <p className="mt-1 text-xs text-slate-300">{s.narrative || s.description}</p>
                      {s.supporting_evidence_ids && s.supporting_evidence_ids.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-1">
                          {s.supporting_evidence_ids.map((id, cIdx) => (
                            <span key={cIdx} className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] font-mono text-slate-400">
                              Ref: {id.slice(0, 8)}...
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Growth Areas Card */}
            <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5 backdrop-blur-md">
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <div className="flex items-center space-x-2">
                  <span className="h-2 w-2 rounded-full bg-amber-400"></span>
                  <h3 className="text-sm font-bold text-white">
                    Growth Opportunities ({report.structured_content.growth_areas?.length || 0})
                  </h3>
                </div>
                {viewerRole !== "employee" && editingSection !== "growth_areas" && (
                  <button
                    onClick={() => handleStartEdit("growth_areas", report.structured_content.growth_areas || [])}
                    className="rounded-md border border-slate-700 bg-slate-800 px-2.5 py-1 text-xs font-medium text-slate-300 hover:bg-slate-700 transition"
                  >
                    ✎ Edit Structured JSON
                  </button>
                )}
              </div>

              {editingSection === "growth_areas" ? (
                <div className="mt-4 space-y-3">
                  <textarea
                    rows={6}
                    value={sectionContent}
                    onChange={(e) => setSectionContent(e.target.value)}
                    className="w-full font-mono rounded-lg border border-slate-700 bg-slate-950 p-3 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
                  />
                  <div>
                    <label className="text-[10px] uppercase font-bold text-slate-400">Reason for Change</label>
                    <input
                      type="text"
                      value={sectionReason}
                      onChange={(e) => setSectionReason(e.target.value)}
                      placeholder="e.g. Calibrated development targets with principal engineer"
                      className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
                    />
                  </div>
                  <div className="flex justify-end space-x-2">
                    <button
                      onClick={() => setEditingSection(null)}
                      className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-700"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleSaveSection}
                      disabled={isActionLoading}
                      className="rounded-lg bg-indigo-600 px-4 py-1.5 text-xs font-bold text-white hover:bg-indigo-500 transition"
                    >
                      {isActionLoading ? "Saving Snapshot..." : "Save New Version"}
                    </button>
                  </div>
                </div>
              ) : (
                <div className="mt-3 space-y-3">
                  {(report.structured_content.growth_areas || []).map((g, idx) => (
                    <div key={idx} className="rounded-lg border border-slate-800/80 bg-slate-950/50 p-3">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-amber-300">{g.theme || g.title || "Opportunity"}</span>
                        {g.confidence_score !== undefined && (
                          <span className="text-[10px] text-slate-400">
                            Confidence: {Math.round(g.confidence_score * 100)}%
                          </span>
                        )}
                      </div>
                      <p className="mt-1 text-xs text-slate-300">
                        {g.narrative || g.gap_observed || g.development_suggestion}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Reviewer Private Notes Card */}
            <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5 backdrop-blur-md">
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <div className="flex items-center space-x-2">
                  <span className="h-2 w-2 rounded-full bg-purple-400"></span>
                  <h3 className="text-sm font-bold text-white">Reviewer &amp; Calibration Notes</h3>
                </div>
                {viewerRole !== "employee" && editingSection !== "reviewer_notes" && (
                  <button
                    onClick={() => handleStartEdit("reviewer_notes", report.structured_content.reviewer_notes || "")}
                    className="rounded-md border border-slate-700 bg-slate-800 px-2.5 py-1 text-xs font-medium text-slate-300 hover:bg-slate-700 transition"
                  >
                    ✎ Edit Notes
                  </button>
                )}
              </div>

              {editingSection === "reviewer_notes" ? (
                <div className="mt-4 space-y-3">
                  <textarea
                    rows={4}
                    value={sectionContent}
                    onChange={(e) => setSectionContent(e.target.value)}
                    className="w-full rounded-lg border border-slate-700 bg-slate-950 p-3 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
                    placeholder="Enter confidential reviewer notes or compensation calibration recommendations..."
                  />
                  <div>
                    <label className="text-[10px] uppercase font-bold text-slate-400">Reason for Change</label>
                    <input
                      type="text"
                      value={sectionReason}
                      onChange={(e) => setSectionReason(e.target.value)}
                      placeholder="e.g. Documented committee calibration alignment"
                      className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
                    />
                  </div>
                  <div className="flex justify-end space-x-2">
                    <button
                      onClick={() => setEditingSection(null)}
                      className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-700"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleSaveSection}
                      disabled={isActionLoading}
                      className="rounded-lg bg-indigo-600 px-4 py-1.5 text-xs font-bold text-white hover:bg-indigo-500 transition"
                    >
                      {isActionLoading ? "Saving Snapshot..." : "Save New Version"}
                    </button>
                  </div>
                </div>
              ) : (
                <p className="mt-3 text-xs text-slate-300 italic">
                  {report.structured_content.reviewer_notes || "No reviewer notes recorded."}
                </p>
              )}
            </div>
          </div>
        )}

        {/* ---------------- Tab 2: Version History ---------------- */}
        {report && activeTab === "versions" && (
          <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5 backdrop-blur-md">
            <h3 className="text-sm font-bold text-white mb-4">Immutable Report Versions History</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400 font-semibold uppercase text-[10px]">
                    <th className="py-2.5 px-3">Version</th>
                    <th className="py-2.5 px-3">Status</th>
                    <th className="py-2.5 px-3">Changed Section</th>
                    <th className="py-2.5 px-3">Change Summary</th>
                    <th className="py-2.5 px-3">Author</th>
                    <th className="py-2.5 px-3">Source</th>
                    <th className="py-2.5 px-3">Created At</th>
                    <th className="py-2.5 px-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {versions.map((ver) => (
                    <tr key={ver.version_id} className="hover:bg-slate-800/30 transition">
                      <td className="py-3 px-3">
                        <span className="font-bold text-indigo-300">v{ver.version_number}</span>
                        {ver.version_number === report.version_number && (
                          <span className="ml-2 rounded bg-indigo-500/20 px-1.5 py-0.5 text-[9px] font-bold text-indigo-300">
                            Current
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-3">
                        <span
                          className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${
                            ver.status === "approved"
                              ? "bg-emerald-500/20 text-emerald-400"
                              : ver.status === "revision_requested"
                              ? "bg-amber-500/20 text-amber-400"
                              : "bg-cyan-500/20 text-cyan-400"
                          }`}
                        >
                          {ver.status.replace("_", " ")}
                        </span>
                      </td>
                      <td className="py-3 px-3 font-mono text-slate-300">{ver.changed_section}</td>
                      <td className="py-3 px-3 text-slate-300 max-w-xs truncate">{ver.change_summary || "—"}</td>
                      <td className="py-3 px-3 text-slate-400">{ver.author_role || "system"}</td>
                      <td className="py-3 px-3">
                        {ver.is_ai_generated ? (
                          <span className="rounded bg-purple-500/10 px-2 py-0.5 text-[10px] text-purple-300 border border-purple-500/20">
                            AI Synthesis
                          </span>
                        ) : (
                          <span className="rounded bg-slate-800 px-2 py-0.5 text-[10px] text-slate-300">
                            Human Edit
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-3 text-slate-400">{new Date(ver.created_at).toLocaleString()}</td>
                      <td className="py-3 px-3 text-right">
                        <button
                          onClick={() => handleInspectSnapshot(ver)}
                          className="rounded-md border border-slate-700 bg-slate-800 px-2 py-1 text-[11px] font-medium text-slate-300 hover:bg-slate-700"
                        >
                          Inspect Snapshot
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* ---------------- Tab 3: Version Comparison ---------------- */}
        {report && activeTab === "compare" && (
          <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5 backdrop-blur-md">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between pb-4 border-b border-slate-800 gap-3">
              <div>
                <h3 className="text-sm font-bold text-white">Deterministic Version Diff</h3>
                <p className="text-xs text-slate-400">
                  Calculates unified diffs and structured list changes between any two immutable versions of this report.
                </p>
              </div>

              <div className="flex items-center space-x-2">
                <div className="flex items-center space-x-1.5">
                  <span className="text-xs text-slate-400">From:</span>
                  <select
                    value={fromVersionNumber}
                    onChange={(e) => setFromVersionNumber(e.target.value)}
                    className="rounded border border-slate-700 bg-slate-950 px-2 py-1 text-xs text-slate-200"
                  >
                    {versions.map((v) => (
                      <option key={v.version_number} value={v.version_number}>
                        v{v.version_number} ({v.changed_section})
                      </option>
                    ))}
                  </select>
                </div>

                <div className="flex items-center space-x-1.5">
                  <span className="text-xs text-slate-400">To:</span>
                  <select
                    value={toVersionNumber}
                    onChange={(e) => setToVersionNumber(e.target.value)}
                    className="rounded border border-slate-700 bg-slate-950 px-2 py-1 text-xs text-slate-200"
                  >
                    {versions.map((v) => (
                      <option key={v.version_number} value={v.version_number}>
                        v{v.version_number} ({v.changed_section})
                      </option>
                    ))}
                  </select>
                </div>

                <button
                  onClick={handleCompareVersions}
                  disabled={isComparing || versions.length < 2}
                  className="rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-bold text-white hover:bg-indigo-500 transition disabled:opacity-50"
                >
                  {isComparing ? "Diffing..." : "Compare"}
                </button>
              </div>
            </div>

            {versions.length < 2 && (
              <div className="py-8 text-center text-xs text-slate-400">
                Only 1 version exists. Edit a section above to create version 2 and view comparison diffs.
              </div>
            )}

            {comparisonResult && (
              <div className="mt-6 space-y-4">
                <div className="flex items-center justify-between rounded-lg bg-slate-950/60 p-3 border border-slate-800">
                  <span className="text-xs font-semibold text-slate-300">
                    Comparing <span className="text-indigo-400">v{comparisonResult.from_version_number}</span> →{" "}
                    <span className="text-indigo-400">v{comparisonResult.to_version_number}</span>
                  </span>
                  <div className="flex items-center space-x-3 text-xs">
                    <span className="text-slate-400">
                      Sections modified: <strong className="text-white">{comparisonResult.sections_changed.length}</strong>
                    </span>
                    {comparisonResult.status_changed && (
                      <span className="text-amber-400 font-medium">
                        Status changed ({comparisonResult.from_status} → {comparisonResult.to_status})
                      </span>
                    )}
                  </div>
                </div>

                {comparisonResult.change_summary.length > 0 && (
                  <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-3">
                    <h4 className="text-[11px] font-bold uppercase text-slate-400">Deterministic Change Summary</h4>
                    <ul className="mt-1 list-disc list-inside space-y-0.5 text-xs text-slate-300">
                      {comparisonResult.change_summary.map((bullet, idx) => (
                        <li key={idx}>{bullet}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {Object.entries(comparisonResult.section_diffs).map(([secKey, diff]) => (
                  <div key={secKey} className="rounded-lg border border-slate-800 bg-slate-950/70 p-4">
                    <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                      <span className="text-xs font-bold font-mono text-cyan-300">{secKey}</span>
                      <span className="rounded bg-slate-800 px-2 py-0.5 text-[10px] text-slate-400">
                        {diff.diff_type} diff
                      </span>
                    </div>

                    {diff.unified_diff ? (
                      <pre className="mt-3 overflow-x-auto rounded bg-slate-950 p-3 font-mono text-[11px] leading-relaxed text-slate-300">
                        {diff.unified_diff.split("\n").map((line, lIdx) => {
                          let lineClass = "text-slate-400";
                          if (line.startsWith("+") && !line.startsWith("+++")) lineClass = "text-emerald-400 bg-emerald-950/30";
                          if (line.startsWith("-") && !line.startsWith("---")) lineClass = "text-red-400 bg-red-950/30";
                          if (line.startsWith("@@")) lineClass = "text-indigo-400";
                          return (
                            <div key={lIdx} className={lineClass}>
                              {line}
                            </div>
                          );
                        })}
                      </pre>
                    ) : (
                      <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                        <div className="rounded bg-slate-950 p-2.5 border border-slate-800">
                          <span className="text-[10px] uppercase font-bold text-red-400">Previous (v{comparisonResult.from_version_number})</span>
                          <pre className="mt-1 overflow-x-auto font-mono text-[11px] text-slate-400">
                            {JSON.stringify(diff.previous_value, null, 2)}
                          </pre>
                        </div>
                        <div className="rounded bg-slate-950 p-2.5 border border-slate-800">
                          <span className="text-[10px] uppercase font-bold text-emerald-400">Current (v{comparisonResult.to_version_number})</span>
                          <pre className="mt-1 overflow-x-auto font-mono text-[11px] text-slate-300">
                            {JSON.stringify(diff.current_value, null, 2)}
                          </pre>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ---------------- Tab 4: Governance Audit Trail ---------------- */}
        {report && activeTab === "audit" && (
          <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5 backdrop-blur-md">
            <h3 className="text-sm font-bold text-white mb-4">Traceable Governance Audit Events</h3>
            {auditEvents.length === 0 ? (
              <p className="text-xs text-slate-500 py-4">No audit events recorded for this report.</p>
            ) : (
              <div className="relative pl-6 border-l border-slate-800 space-y-6">
                {auditEvents.map((evt) => (
                  <div key={evt.id} className="relative">
                    <div className="absolute -left-[31px] top-1 h-3 w-3 rounded-full border-2 border-slate-900 bg-indigo-500"></div>
                    <div className="flex items-center space-x-2">
                      <span className="font-mono text-xs font-bold text-indigo-300">{evt.action}</span>
                      <span className="text-[10px] text-slate-500">{new Date(evt.created_at).toLocaleString()}</span>
                    </div>
                    <div className="mt-1 text-xs text-slate-300">
                      Actor: <span className="font-semibold text-white">{evt.actor_name || "Manager"}</span>{" "}
                      <span className="text-slate-400 font-mono">({evt.actor_role || "manager"})</span>
                    </div>
                    {evt.metadata_json && Object.keys(evt.metadata_json).length > 0 && (
                      <pre className="mt-2 overflow-x-auto rounded bg-slate-950 p-2 text-[10px] font-mono text-slate-400 border border-slate-800/60">
                        {JSON.stringify(evt.metadata_json, null, 2)}
                      </pre>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Snapshot Inspection Modal */}
      {inspectedVersion && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-sm">
          <div className="relative max-h-[85vh] w-full max-w-3xl overflow-y-auto rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div>
                <h3 className="text-base font-bold text-white">
                  Historical Snapshot: v{inspectedVersion.version_number}
                </h3>
                <p className="text-xs text-slate-400">
                  {inspectedVersion.change_summary} · Created {new Date(inspectedVersion.created_at).toLocaleString()}
                </p>
              </div>
              <button
                onClick={() => setInspectedVersion(null)}
                className="rounded-lg bg-slate-800 p-1.5 text-slate-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            {isLoadingSnapshot ? (
              <div className="py-12 text-center text-xs text-slate-400">Loading snapshot data...</div>
            ) : inspectedContent ? (
              <div className="mt-4 space-y-4 text-xs">
                <div>
                  <h4 className="font-semibold text-slate-300 uppercase text-[10px] tracking-wider">Executive Summary</h4>
                  <p className="mt-1 rounded bg-slate-950 p-3 text-slate-300 whitespace-pre-wrap">
                    {inspectedContent.executive_summary || "None"}
                  </p>
                </div>
                <div>
                  <h4 className="font-semibold text-slate-300 uppercase text-[10px] tracking-wider">Strengths</h4>
                  <pre className="mt-1 overflow-x-auto rounded bg-slate-950 p-3 font-mono text-[11px] text-emerald-300">
                    {JSON.stringify(inspectedContent.strengths, null, 2)}
                  </pre>
                </div>
                <div>
                  <h4 className="font-semibold text-slate-300 uppercase text-[10px] tracking-wider">Growth Areas</h4>
                  <pre className="mt-1 overflow-x-auto rounded bg-slate-950 p-3 font-mono text-[11px] text-amber-300">
                    {JSON.stringify(inspectedContent.growth_areas, null, 2)}
                  </pre>
                </div>
              </div>
            ) : (
              <div className="py-6 text-center text-xs text-slate-400">No snapshot content available.</div>
            )}
          </div>
        </div>
      )}

      {/* Deliberate Human Approval / Revision Request Modal */}
      {approvalModalMode && report && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-sm">
          <div className="relative w-full max-w-lg rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-2xl">
            <h3 className="text-base font-bold text-white">
              {approvalModalMode === "approve"
                ? `Deliberate Approval: Finalize Version ${report.version_number}`
                : `Request Revisions for Version ${report.version_number}`}
            </h3>
            <p className="mt-1 text-xs text-slate-400">
              {approvalModalMode === "approve"
                ? "This action will bind immutable human sign-off to this exact version snapshot. Stale modifications will be strictly guarded against."
                : "Please supply mandatory instructions for the review adjustments required."}
            </p>

            <div className="mt-4">
              <label className="text-[10px] uppercase font-bold text-slate-400">
                {approvalModalMode === "approve" ? "Reviewer Comments (Optional)" : "Revision Instructions (Mandatory)"}
              </label>
              <textarea
                rows={4}
                value={approvalComments}
                onChange={(e) => setApprovalComments(e.target.value)}
                placeholder={
                  approvalModalMode === "approve"
                    ? "e.g. Thoroughly vetted against engineering matrix. Ready for delivery."
                    : "e.g. Please clarify the caching benchmarks and add code review impact stats."
                }
                className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 p-3 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
              />
            </div>

            <div className="mt-6 flex justify-end space-x-3">
              <button
                onClick={() => {
                  setApprovalModalMode(null);
                  setApprovalComments("");
                }}
                className="rounded-lg border border-slate-700 bg-slate-800 px-4 py-2 text-xs font-semibold text-slate-300 hover:bg-slate-700"
              >
                Cancel
              </button>
              {approvalModalMode === "approve" ? (
                <button
                  onClick={handleApproveReport}
                  disabled={isActionLoading}
                  className="rounded-lg bg-emerald-600 px-5 py-2 text-xs font-bold text-white hover:bg-emerald-500 transition shadow-lg shadow-emerald-900/40"
                >
                  {isActionLoading ? "Finalizing Sign-Off..." : "Confirm & Sign Off"}
                </button>
              ) : (
                <button
                  onClick={handleRequestRevision}
                  disabled={isActionLoading}
                  className="rounded-lg bg-amber-600 px-5 py-2 text-xs font-bold text-white hover:bg-amber-500 transition shadow-lg shadow-amber-900/40"
                >
                  {isActionLoading ? "Submitting..." : "Submit Revision Request"}
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
