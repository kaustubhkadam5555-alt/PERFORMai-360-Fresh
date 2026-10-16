"use client";

import React, { useEffect, useState } from "react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  PieChart,
  Pie,
  Cell,
  AreaChart,
  Area,
} from "recharts";

interface AnalyticsOverview {
  total_cycles: number;
  active_cycles: number;
  finalized_cycles: number;
  completion_rate: number;
  completion_numerator: number;
  completion_denominator: number;
  completion_definition: string;
  total_evidence_records: number;
  total_reports: number;
  total_approvals: number;
  total_revision_requests: number;
  average_audit_health_score: number | null;
  generated_at: string;
}

interface ReviewAnalytics {
  cycles: Array<{
    cycle_id: string;
    title: string;
    employee_id: string;
    status: string;
    created_at: string;
    workflow_completed: boolean;
    report_approved: boolean;
  }>;
  status_distribution: Record<string, number>;
  total: number;
}

interface EvidenceAnalytics {
  total_evidence: number;
  source_distribution: Record<string, number>;
  policy_distribution: Record<string, number>;
  cited_claims_count: number;
  ungrounded_claims_count: number;
}

interface AuditAnalytics {
  total_flags: number;
  flags_by_rule: Record<string, number>;
  flags_by_severity: Record<string, number>;
  flags_by_status: Record<string, number>;
  average_health_score: number | null;
  score_distribution: Record<string, number>;
}

interface TrendPoint {
  date_bucket: string;
  review_cycles_created: number;
  evidence_uploaded: number;
  reports_approved: number;
}

interface TrendsAnalytics {
  interval: string;
  points: TrendPoint[];
}

const PALETTE = {
  indigo: "#6366f1",
  purple: "#a855f7",
  cyan: "#06b6d4",
  emerald: "#10b981",
  amber: "#f59e0b",
  rose: "#f43f5e",
  slate: "#64748b",
};

const PIE_COLORS = ["#6366f1", "#10b981", "#f59e0b", "#06b6d4", "#f43f5e", "#a855f7", "#ec4899"];

export function AnalyticsDashboardCard() {
  const mounted = React.useSyncExternalStore(
    () => () => {},
    () => true,
    () => false
  );
  const [viewerRole, setViewerRole] = useState<string>("manager");
  const [dateInterval, setDateInterval] = useState<"day" | "week" | "month">("week");
  const [startDate, setStartDate] = useState<string>("");
  const [endDate, setEndDate] = useState<string>("");
  const [showDataTables, setShowDataTables] = useState<boolean>(false);
  const [refreshKey, setRefreshKey] = useState<number>(0);

  // Data states
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [reviews, setReviews] = useState<ReviewAnalytics | null>(null);
  const [evidence, setEvidence] = useState<EvidenceAnalytics | null>(null);
  const [audits, setAudits] = useState<AuditAnalytics | null>(null);
  const [trends, setTrends] = useState<TrendsAnalytics | null>(null);

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const rawApiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const backendBaseUrl = rawApiUrl.replace(/\/api\/v1\/?$/, "").replace(/\/+$/, "");

  useEffect(() => {
    let ignore = false;

    async function loadData() {
      const queryParams = new URLSearchParams();
      if (startDate) queryParams.append("start_date", startDate);
      if (endDate) queryParams.append("end_date", endDate);
      const dateQuery = queryParams.toString() ? `?${queryParams.toString()}` : "";

      const trendsQuery = new URLSearchParams(queryParams);
      trendsQuery.append("interval", dateInterval);
      const trendsUrlQuery = `?${trendsQuery.toString()}`;

      const headers = {
        "X-Viewer-Role": viewerRole,
      };

      try {
        const [ovRes, revRes, evRes, audRes, trRes] = await Promise.all([
          fetch(`${backendBaseUrl}/api/v1/analytics/overview${dateQuery}`, { headers, cache: "no-store" }),
          fetch(`${backendBaseUrl}/api/v1/analytics/reviews${dateQuery}`, { headers, cache: "no-store" }),
          fetch(`${backendBaseUrl}/api/v1/analytics/evidence${dateQuery}`, { headers, cache: "no-store" }),
          fetch(`${backendBaseUrl}/api/v1/analytics/audits${dateQuery}`, { headers, cache: "no-store" }),
          fetch(`${backendBaseUrl}/api/v1/analytics/trends${trendsUrlQuery}`, { headers, cache: "no-store" }),
        ]);

        if (!ovRes.ok) {
          const err = await ovRes.json().catch(() => ({}));
          throw new Error(err.detail || `HTTP ${ovRes.status}: Failed to load overview`);
        }

        const ovData: AnalyticsOverview = await ovRes.json();
        if (!ignore) {
          setOverview(ovData);
          if (revRes.ok) setReviews(await revRes.json());
          if (evRes.ok) setEvidence(await evRes.json());
          if (audRes.ok) setAudits(await audRes.json());
          if (trRes.ok) setTrends(await trRes.json());
        }
      } catch (err: unknown) {
        if (!ignore) {
          setErrorMessage(err instanceof Error ? err.message : "Failed to load analytics dashboard data.");
        }
      } finally {
        if (!ignore) {
          setIsLoading(false);
        }
      }
    }

    loadData();

    return () => {
      ignore = true;
    };
  }, [backendBaseUrl, viewerRole, startDate, endDate, dateInterval, refreshKey]);

  const handleRefresh = () => {
    setIsLoading(true);
    setErrorMessage(null);
    setRefreshKey((k) => k + 1);
  };

  // Chart data transforms
  const statusChartData = reviews
    ? Object.entries(reviews.status_distribution).map(([status, count]) => ({
        name: status.replace("_", " ").toUpperCase(),
        count,
      }))
    : [];

  const evidenceSourceData = evidence
    ? Object.entries(evidence.source_distribution).map(([source, count]) => ({
        name: source.replace("_", " ").toUpperCase(),
        value: count,
      }))
    : [];

  const auditRulesData = audits
    ? Object.entries(audits.flags_by_rule).map(([rule, count]) => ({
        rule: rule.replace("_", " "),
        flags: count,
      }))
    : [];

  const trendData = trends
    ? trends.points.map((pt) => ({
        date: pt.date_bucket,
        cycles: pt.review_cycles_created,
        evidence: pt.evidence_uploaded,
        approvals: pt.reports_approved,
      }))
    : [];

  return (
    <section
      id="analytics"
      aria-labelledby="analytics-dashboard-title"
      className="mt-14 rounded-2xl border border-slate-800 bg-slate-900/40 p-6 backdrop-blur-xl shadow-2xl relative overflow-hidden"
    >
      {/* Background ambient gradient */}
      <div className="pointer-events-none absolute -right-20 -top-20 h-72 w-72 rounded-full bg-indigo-500/10 blur-3xl" />
      <div className="pointer-events-none absolute -left-20 -bottom-20 h-72 w-72 rounded-full bg-purple-500/10 blur-3xl" />

      {/* Header and Controls */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between pb-6 border-b border-slate-800 gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <span className="inline-flex items-center rounded-md bg-indigo-500/10 px-2.5 py-1 text-xs font-semibold text-indigo-400 border border-indigo-500/20">
              Phase 9 Analytics
            </span>
            <span className="text-xs text-slate-400">Live PostgreSQL Metrics</span>
          </div>
          <h2 id="analytics-dashboard-title" className="mt-2 text-2xl font-bold tracking-tight text-white">
            Performance &amp; Governance Analytics Dashboard
          </h2>
          <p className="mt-1 text-xs text-slate-400 max-w-2xl">
            Real-time evaluation metrics, completion rates with strict mathematical definitions, deterministic bias
            findings, and cross-cycle evidence coverage.
          </p>
        </div>

        {/* Global Filter Bar */}
        <div className="flex flex-wrap items-center gap-3 text-xs">
          {/* Role selector */}
          <div className="flex items-center space-x-1.5">
            <label htmlFor="analytics-role-select" className="text-slate-400 font-medium">
              Role:
            </label>
            <select
              id="analytics-role-select"
              value={viewerRole}
              onChange={(e) => setViewerRole(e.target.value)}
              className="rounded-lg border border-slate-700 bg-slate-800 px-2.5 py-1.5 text-xs text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
            >
              <option value="manager">Manager (Scoped)</option>
              <option value="admin">Admin (Global)</option>
              <option value="employee">Employee (Self-Only)</option>
            </select>
          </div>

          {/* Date range inputs */}
          <div className="flex items-center space-x-1.5">
            <label htmlFor="analytics-start-date" className="text-slate-400 font-medium">
              From:
            </label>
            <input
              id="analytics-start-date"
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="rounded-lg border border-slate-700 bg-slate-800 px-2 py-1 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
            <label htmlFor="analytics-end-date" className="text-slate-400 font-medium">
              To:
            </label>
            <input
              id="analytics-end-date"
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="rounded-lg border border-slate-700 bg-slate-800 px-2 py-1 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>

          {/* Interval */}
          <div className="flex items-center space-x-1.5">
            <label htmlFor="analytics-interval-select" className="text-slate-400 font-medium">
              Interval:
            </label>
            <select
              id="analytics-interval-select"
              value={dateInterval}
              onChange={(e) => setDateInterval(e.target.value as "day" | "week" | "month")}
              className="rounded-lg border border-slate-700 bg-slate-800 px-2 py-1.5 text-xs text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
            >
              <option value="day">Day</option>
              <option value="week">Week</option>
              <option value="month">Month</option>
            </select>
          </div>

          {/* Accessible Table View Toggle */}
          <button
            type="button"
            onClick={() => setShowDataTables((prev) => !prev)}
            aria-pressed={showDataTables}
            className={`rounded-lg border px-3 py-1.5 text-xs font-semibold transition ${
              showDataTables
                ? "border-cyan-500/60 bg-cyan-500/20 text-cyan-300"
                : "border-slate-700 bg-slate-800 text-slate-300 hover:bg-slate-700"
            }`}
          >
            {showDataTables ? "Hide Data Tables" : "Show Accessible Tables (WCAG)"}
          </button>

          {/* Refresh button */}
          <button
            type="button"
            onClick={handleRefresh}
            disabled={isLoading}
            aria-label="Refresh analytics dashboard"
            className="rounded-lg border border-indigo-500/40 bg-indigo-600/30 px-3 py-1.5 text-xs font-semibold text-indigo-200 hover:bg-indigo-600/50 transition disabled:opacity-50"
          >
            {isLoading ? "Refreshing..." : "↻ Refresh"}
          </button>
        </div>
      </div>

      {/* Screen reader live notification */}
      <div role="status" aria-live="polite" className="sr-only">
        {isLoading
          ? "Loading analytics data"
          : errorMessage
          ? `Error loading analytics: ${errorMessage}`
          : "Analytics dashboard loaded"}
      </div>

      {/* Error alert */}
      {errorMessage && (
        <div className="mt-4 rounded-xl border border-red-500/40 bg-red-950/40 p-4 text-xs text-red-300">
          <p className="font-semibold">Analytics Error:</p>
          <p className="mt-1">{errorMessage}</p>
        </div>
      )}

      {/* Key Metric Overview Cards */}
      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {/* Metric 1: Total Review Cycles */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Total Review Cycles</span>
            <span className="rounded bg-indigo-500/10 px-2 py-0.5 text-[10px] font-bold text-indigo-400">
              Active: {overview?.active_cycles ?? 0}
            </span>
          </div>
          <div className="mt-2 flex items-baseline space-x-2">
            <span className="text-2xl font-extrabold text-white">
              {isLoading ? "..." : overview?.total_cycles ?? 0}
            </span>
            <span className="text-xs text-slate-400">
              cycles ({overview?.finalized_cycles ?? 0} finalized)
            </span>
          </div>
          <p className="mt-2 text-[11px] text-slate-400">
            Lifecycle tracking from drafted to finalized sign-offs.
          </p>
        </div>

        {/* Metric 2: Completion Rate */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Cycle Completion Rate</span>
            <span className="rounded bg-emerald-500/10 px-2 py-0.5 text-[10px] font-bold text-emerald-400">
              {overview?.completion_numerator ?? 0} / {overview?.completion_denominator ?? 0}
            </span>
          </div>
          <div className="mt-2 flex items-baseline space-x-2">
            <span className="text-2xl font-extrabold text-emerald-400">
              {isLoading ? "..." : `${overview?.completion_rate ?? 0}%`}
            </span>
          </div>
          <p
            className="mt-2 text-[11px] text-slate-400 truncate"
            title={overview?.completion_definition || "Finalized cycles / Total cycles"}
          >
            {overview?.completion_definition || "Completed reviews ratio"}
          </p>
        </div>

        {/* Metric 3: Evidence Records & Citations */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Evidence Records</span>
            <span className="rounded bg-cyan-500/10 px-2 py-0.5 text-[10px] font-bold text-cyan-400">
              Cited: {evidence?.cited_claims_count ?? 0}
            </span>
          </div>
          <div className="mt-2 flex items-baseline space-x-2">
            <span className="text-2xl font-extrabold text-cyan-300">
              {isLoading ? "..." : overview?.total_evidence_records ?? 0}
            </span>
            <span className="text-xs text-slate-400">ingested artifacts</span>
          </div>
          <p className="mt-2 text-[11px] text-slate-400">
            Ungrounded claims: {evidence?.ungrounded_claims_count ?? 0}
          </p>
        </div>

        {/* Metric 4: Average Audit Health Score */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Audit Health Score</span>
            <span
              className={`rounded px-2 py-0.5 text-[10px] font-bold ${
                (overview?.average_audit_health_score ?? 100) >= 80
                  ? "bg-emerald-500/10 text-emerald-400"
                  : "bg-amber-500/10 text-amber-400"
              }`}
            >
              {(overview?.average_audit_health_score ?? 100) >= 80 ? "Healthy" : "Review Needed"}
            </span>
          </div>
          <div className="mt-2 flex items-baseline space-x-2">
            <span className="text-2xl font-extrabold text-white">
              {isLoading
                ? "..."
                : overview?.average_audit_health_score !== null && overview?.average_audit_health_score !== undefined
                ? `${overview.average_audit_health_score.toFixed(1)}/100`
                : "100.0/100"}
            </span>
          </div>
          <p className="mt-2 text-[11px] text-slate-400">
            Total Bias &amp; Evidence Flags: {audits?.total_flags ?? 0}
          </p>
        </div>
      </div>

      {/* Governance Counter Bar */}
      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-800 bg-slate-950/60 px-4 py-2.5 text-xs text-slate-400">
        <div className="flex items-center space-x-4">
          <span>
            <strong className="text-slate-200">Reports Generated:</strong> {overview?.total_reports ?? 0}
          </span>
          <span>
            <strong className="text-emerald-400">Approvals Recorded:</strong> {overview?.total_approvals ?? 0}
          </span>
          <span>
            <strong className="text-amber-400">Revisions Requested:</strong> {overview?.total_revision_requests ?? 0}
          </span>
        </div>
        <div className="text-[11px] text-slate-400 font-mono">
          Last computed: {overview?.generated_at ? new Date(overview.generated_at).toLocaleTimeString() : "—"}
        </div>
      </div>

      {/* Charts Grid */}
      <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Chart 1: Cycle Status Distribution */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div>
              <h3 className="text-sm font-bold text-white">Review Cycle Lifecycle Distribution</h3>
              <p className="text-xs text-slate-400">Current workflow states of evaluated cycles</p>
            </div>
            <span className="text-xs text-indigo-400 font-mono font-semibold">
              Total: {reviews?.total ?? 0}
            </span>
          </div>

          <div className="mt-4 h-64 w-full">
            {mounted && statusChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={statusChartData} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
                  <XAxis dataKey="name" stroke="#94a3b8" fontSize={11} interval={0} angle={-15} textAnchor="end" />
                  <YAxis stroke="#94a3b8" fontSize={11} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{ backgroundColor: "#0f172a", borderColor: "#334155", borderRadius: "8px" }}
                    labelStyle={{ color: "#f8fafc", fontWeight: "bold" }}
                  />
                  <Bar dataKey="count" fill={PALETTE.indigo} radius={[4, 4, 0, 0]} name="Cycles" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center text-xs text-slate-400">
                {isLoading ? "Loading lifecycle data..." : "No review cycles found."}
              </div>
            )}
          </div>

          {/* Accessible Table Fallback */}
          {showDataTables && statusChartData.length > 0 && (
            <div className="mt-4 border-t border-slate-800 pt-3 overflow-x-auto">
              <table className="min-w-full text-xs text-left">
                <caption className="text-slate-400 sr-only">Review Cycle Lifecycle Breakdown</caption>
                <thead>
                  <tr className="border-b border-slate-800 text-slate-300">
                    <th scope="col" className="py-1 px-2 font-semibold">Lifecycle Status</th>
                    <th scope="col" className="py-1 px-2 font-semibold text-right">Cycle Count</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {statusChartData.map((row) => (
                    <tr key={row.name}>
                      <td className="py-1 px-2 text-slate-300">{row.name}</td>
                      <td className="py-1 px-2 text-right font-mono text-indigo-300">{row.count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Chart 2: Evidence Source Breakdown */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div>
              <h3 className="text-sm font-bold text-white">Evidence Source Distribution</h3>
              <p className="text-xs text-slate-400">Artifacts ingested by integration source</p>
            </div>
            <span className="text-xs text-cyan-400 font-mono font-semibold">
              Total: {evidence?.total_evidence ?? 0}
            </span>
          </div>

          <div className="mt-4 h-64 w-full">
            {mounted && evidenceSourceData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={evidenceSourceData}
                    cx="50%"
                    cy="50%"
                    outerRadius={80}
                    innerRadius={45}
                    paddingAngle={3}
                    dataKey="value"
                    label={({ name, percent }) => `${name} ${((percent || 0) * 100).toFixed(0)}%`}
                    labelLine={false}
                  >
                    {evidenceSourceData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ backgroundColor: "#0f172a", borderColor: "#334155", borderRadius: "8px" }}
                    itemStyle={{ color: "#f8fafc" }}
                  />
                  <Legend verticalAlign="bottom" height={36} wrapperStyle={{ fontSize: "11px", color: "#94a3b8" }} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center text-xs text-slate-400">
                {isLoading ? "Loading evidence data..." : "No evidence records ingested."}
              </div>
            )}
          </div>

          {/* Accessible Table Fallback */}
          {showDataTables && evidenceSourceData.length > 0 && (
            <div className="mt-4 border-t border-slate-800 pt-3 overflow-x-auto">
              <table className="min-w-full text-xs text-left">
                <caption className="text-slate-400 sr-only">Evidence Source Breakdown</caption>
                <thead>
                  <tr className="border-b border-slate-800 text-slate-300">
                    <th scope="col" className="py-1 px-2 font-semibold">Source Type</th>
                    <th scope="col" className="py-1 px-2 font-semibold text-right">Records Ingested</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {evidenceSourceData.map((row) => (
                    <tr key={row.name}>
                      <td className="py-1 px-2 text-slate-300">{row.name}</td>
                      <td className="py-1 px-2 text-right font-mono text-cyan-300">{row.value}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Chart 3: Deterministic Bias & Evidence Audit Flags */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div>
              <h3 className="text-sm font-bold text-white">Bias Audit Findings by Rule</h3>
              <p className="text-xs text-slate-400">Deterministic flags detected by audit engine</p>
            </div>
            <span className="text-xs text-amber-400 font-mono font-semibold">
              Total Flags: {audits?.total_flags ?? 0}
            </span>
          </div>

          <div className="mt-4 h-64 w-full">
            {mounted && auditRulesData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={auditRulesData} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
                  <XAxis dataKey="rule" stroke="#94a3b8" fontSize={10} interval={0} angle={-20} textAnchor="end" />
                  <YAxis stroke="#94a3b8" fontSize={11} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{ backgroundColor: "#0f172a", borderColor: "#334155", borderRadius: "8px" }}
                    labelStyle={{ color: "#f8fafc", fontWeight: "bold" }}
                  />
                  <Bar dataKey="flags" fill={PALETTE.amber} radius={[4, 4, 0, 0]} name="Audit Flags" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center text-xs text-slate-400">
                {isLoading ? "Loading audit findings..." : "No bias audit flags detected (100% Clean)."}
              </div>
            )}
          </div>

          {/* Accessible Table Fallback */}
          {showDataTables && auditRulesData.length > 0 && (
            <div className="mt-4 border-t border-slate-800 pt-3 overflow-x-auto">
              <table className="min-w-full text-xs text-left">
                <caption className="text-slate-400 sr-only">Bias Audit Findings Breakdown</caption>
                <thead>
                  <tr className="border-b border-slate-800 text-slate-300">
                    <th scope="col" className="py-1 px-2 font-semibold">Audit Rule</th>
                    <th scope="col" className="py-1 px-2 font-semibold text-right">Flags Identified</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {auditRulesData.map((row) => (
                    <tr key={row.rule}>
                      <td className="py-1 px-2 text-slate-300 capitalize">{row.rule}</td>
                      <td className="py-1 px-2 text-right font-mono text-amber-300">{row.flags}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Chart 4: Activity Trends Over Time */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div>
              <h3 className="text-sm font-bold text-white">Activity Trends Over Time</h3>
              <p className="text-xs text-slate-400">
                Cycles created, evidence ingested &amp; approved reports ({dateInterval}ly)
              </p>
            </div>
            <span className="text-xs text-emerald-400 font-mono font-semibold">
              Interval: {dateInterval}
            </span>
          </div>

          <div className="mt-4 h-64 w-full">
            {mounted && trendData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={trendData} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
                  <defs>
                    <linearGradient id="colorEvidence" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={PALETTE.cyan} stopOpacity={0.8} />
                      <stop offset="95%" stopColor={PALETTE.cyan} stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="colorCycles" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={PALETTE.indigo} stopOpacity={0.8} />
                      <stop offset="95%" stopColor={PALETTE.indigo} stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="colorApprovals" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={PALETTE.emerald} stopOpacity={0.8} />
                      <stop offset="95%" stopColor={PALETTE.emerald} stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
                  <XAxis dataKey="date" stroke="#94a3b8" fontSize={11} />
                  <YAxis stroke="#94a3b8" fontSize={11} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{ backgroundColor: "#0f172a", borderColor: "#334155", borderRadius: "8px" }}
                    labelStyle={{ color: "#f8fafc", fontWeight: "bold" }}
                  />
                  <Legend verticalAlign="bottom" height={36} wrapperStyle={{ fontSize: "11px", color: "#94a3b8" }} />
                  <Area
                    type="monotone"
                    dataKey="evidence"
                    stroke={PALETTE.cyan}
                    fillOpacity={1}
                    fill="url(#colorEvidence)"
                    name="Evidence Uploaded"
                  />
                  <Area
                    type="monotone"
                    dataKey="cycles"
                    stroke={PALETTE.indigo}
                    fillOpacity={1}
                    fill="url(#colorCycles)"
                    name="Cycles Created"
                  />
                  <Area
                    type="monotone"
                    dataKey="approvals"
                    stroke={PALETTE.emerald}
                    fillOpacity={1}
                    fill="url(#colorApprovals)"
                    name="Reports Approved"
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center text-xs text-slate-400">
                {isLoading ? "Loading activity trends..." : "No trend activity recorded in interval."}
              </div>
            )}
          </div>

          {/* Accessible Table Fallback */}
          {showDataTables && trendData.length > 0 && (
            <div className="mt-4 border-t border-slate-800 pt-3 overflow-x-auto">
              <table className="min-w-full text-xs text-left">
                <caption className="text-slate-400 sr-only">Activity Trends Table</caption>
                <thead>
                  <tr className="border-b border-slate-800 text-slate-300">
                    <th scope="col" className="py-1 px-2 font-semibold">Date Bucket</th>
                    <th scope="col" className="py-1 px-2 font-semibold text-right">Cycles</th>
                    <th scope="col" className="py-1 px-2 font-semibold text-right">Evidence</th>
                    <th scope="col" className="py-1 px-2 font-semibold text-right">Approvals</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {trendData.map((row) => (
                    <tr key={row.date}>
                      <td className="py-1 px-2 text-slate-300 font-mono">{row.date}</td>
                      <td className="py-1 px-2 text-right font-mono text-indigo-300">{row.cycles}</td>
                      <td className="py-1 px-2 text-right font-mono text-cyan-300">{row.evidence}</td>
                      <td className="py-1 px-2 text-right font-mono text-emerald-300">{row.approvals}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
