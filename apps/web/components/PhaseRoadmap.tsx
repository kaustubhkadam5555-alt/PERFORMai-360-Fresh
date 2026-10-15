"use client";

import React from "react";

interface Phase {
  phase: string;
  name: string;
  status: "completed" | "current" | "upcoming";
  summary: string;
}

export function PhaseRoadmap() {
  const phases: Phase[] = [
    {
      phase: "Phase 0",
      name: "Repository & Planning Baseline",
      status: "completed",
      summary: "PRD analysis, baseline docs, .gitignore, .env.example, runtime verification.",
    },
    {
      phase: "Phase 1",
      name: "Application Foundation",
      status: "current",
      summary: "Next.js 16 frontend, FastAPI backend, PostgreSQL Docker Compose, health & readiness probes.",
    },
    {
      phase: "Phase 2",
      name: "Database, Migrations & Auth",
      status: "upcoming",
      summary: "SQLAlchemy models, Alembic migrations, server-side RBAC, synthetic seed data.",
    },
    {
      phase: "Phase 3",
      name: "Core Review Workflow",
      status: "upcoming",
      summary: "Review-cycle state machine, self/peer/manager feedback forms, goal tracking.",
    },
    {
      phase: "Phase 4",
      name: "Evidence Processing & Retrieval",
      status: "upcoming",
      summary: "Safe document parsing (PDF, DOCX, TXT), scoped retrieval, employee isolation.",
    },
    {
      phase: "Phase 5",
      name: "Single-Pass AI Analysis",
      status: "upcoming",
      summary: "Provider-neutral adapter, structured extraction, source-ID grounding validation.",
    },
    {
      phase: "Phase 6",
      name: "Bias & Evidence-Quality Audit",
      status: "upcoming",
      summary: "Deterministic checks: recency concentration, stakeholder balance, ungrounded claims.",
    },
    {
      phase: "Phase 7",
      name: "LangGraph Multi-Agent Engine",
      status: "upcoming",
      summary: "4 specialist agent nodes, typed state graph, bounded retries, approval pause.",
    },
    {
      phase: "Phase 8",
      name: "Human Approval & Report Governance",
      status: "upcoming",
      summary: "Draft report editing, approval/revision actions, versioning, immutable audit log.",
    },
    {
      phase: "Phase 9",
      name: "Dashboard Polish & Accessibility",
      status: "upcoming",
      summary: "Analytics charts (Recharts), WCAG accessibility, keyboard navigation, export.",
    },
    {
      phase: "Phase 10",
      name: "Comprehensive Testing & Security",
      status: "upcoming",
      summary: "Playwright E2E tests, permission barrier verification, security audit.",
    },
    {
      phase: "Phase 11",
      name: "Documentation & Demo Readiness",
      status: "upcoming",
      summary: "Clean demonstration scenario, documented evaluation metrics, faculty walkthrough.",
    },
  ];

  return (
    <div id="roadmap" className="mt-14">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white sm:text-3xl">
            Phased Implementation Roadmap
          </h2>
          <p className="mt-1 text-sm text-slate-400">
            Strict sequential execution governed by PRD Section 15. One phase at a time.
          </p>
        </div>
        <div className="mt-3 sm:mt-0 flex items-center space-x-2 text-xs">
          <span className="flex items-center text-emerald-400">
            <span className="mr-1 h-2 w-2 rounded-full bg-emerald-400"></span> Completed
          </span>
          <span className="flex items-center text-indigo-400 ml-3">
            <span className="mr-1 h-2 w-2 rounded-full bg-indigo-400 animate-pulse"></span> Active
          </span>
          <span className="flex items-center text-slate-500 ml-3">
            <span className="mr-1 h-2 w-2 rounded-full bg-slate-700"></span> Upcoming
          </span>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {phases.map((item, idx) => (
          <div
            key={idx}
            className={`rounded-xl p-4 transition-all border ${
              item.status === "completed"
                ? "bg-slate-900/50 border-emerald-500/30"
                : item.status === "current"
                ? "glass-panel border-indigo-500/60 shadow-lg shadow-indigo-500/10"
                : "bg-slate-950/40 border-slate-900 text-slate-500"
            }`}
          >
            <div className="flex items-center justify-between">
              <span
                className={`text-xs font-mono font-semibold px-2 py-0.5 rounded ${
                  item.status === "completed"
                    ? "bg-emerald-500/10 text-emerald-400"
                    : item.status === "current"
                    ? "bg-indigo-500/20 text-indigo-300 border border-indigo-500/40"
                    : "bg-slate-900 text-slate-500"
                }`}
              >
                {item.phase}
              </span>
              {item.status === "completed" && (
                <span className="text-xs font-semibold text-emerald-400 flex items-center">
                  <svg className="h-3.5 w-3.5 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                  </svg>
                  Verified
                </span>
              )}
              {item.status === "current" && (
                <span className="text-xs font-semibold text-indigo-400 flex items-center">
                  <span className="h-1.5 w-1.5 rounded-full bg-indigo-400 mr-1.5 animate-ping"></span>
                  In Progress
                </span>
              )}
            </div>

            <h4
              className={`mt-2.5 text-sm font-bold ${
                item.status === "upcoming" ? "text-slate-400" : "text-white"
              }`}
            >
              {item.name}
            </h4>
            <p className="mt-1 text-xs text-slate-400 leading-relaxed">{item.summary}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
