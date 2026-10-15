"use client";

import React from "react";

interface Pillar {
  title: string;
  tagline: string;
  description: string;
  badge: string;
  badgeColor: string;
  icon: React.ReactNode;
  specs: string[];
}

export function PillarCards() {
  const pillars: Pillar[] = [
    {
      title: "360° Evidence Aggregator",
      tagline: "Comprehensive Multi-Stakeholder Ingestion",
      description:
        "Ingests employee self-assessments, peer evaluations, manager reviews, measurable goals, and authorized project evidence within a defined review cycle.",
      badge: "PRD Section 4 & 7",
      badgeColor: "bg-blue-500/10 text-blue-400 border-blue-500/30",
      specs: ["Scoped RBAC Retrieval", "Direct Source ID Grounding", "Cross-Employee Isolation"],
      icon: (
        <svg className="h-6 w-6 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.75}
            d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
          />
        </svg>
      ),
    },
    {
      title: "Deterministic Bias & Quality Audit",
      tagline: "Explainable Anomaly & Imbalance Detection",
      description:
        "Transparent rule-based heuristics detect review-period recency concentration, stakeholder imbalances, vague absolute assertions ('always'/'never'), and ungrounded claims.",
      badge: "PRD Section 7 (FR-09)",
      badgeColor: "bg-purple-500/10 text-purple-400 border-purple-500/30",
      specs: ["Recency Window Checks", "Evidence Coverage Flags", "Actionable Reviewer Prompts"],
      icon: (
        <svg className="h-6 w-6 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.75}
            d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3"
          />
        </svg>
      ),
    },
    {
      title: "LangGraph Multi-Agent Engine",
      tagline: "Observable State Machine & Pauses",
      description:
        "Orchestrates four specialized logical nodes: Evidence Retrieval, Feedback Analysis, Bias Auditor, and Review Synthesis, paused deterministically before human approval.",
      badge: "PRD Section 7 (FR-10)",
      badgeColor: "bg-indigo-500/10 text-indigo-400 border-indigo-500/30",
      specs: ["Typed Pydantic Schemas", "Approval Pause Node", "Safe Bounded Retries"],
      icon: (
        <svg className="h-6 w-6 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.75}
            d="M13 10V3L4 14h7v7l9-11h-7z"
          />
        </svg>
      ),
    },
    {
      title: "Human-in-the-Loop Governance",
      tagline: "Mandatory Approvals & Tamper-Proof Audit",
      description:
        "AI drafts cannot be finalized autonomously. Authorized managers must review citations, resolve flags, edit drafts, and sign off. Every lifecycle change is recorded in an immutable log.",
      badge: "PRD Section 7 (FR-12 & 13)",
      badgeColor: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
      specs: ["Immutable Version History", "Human Edit Preservation", "Append-Only Audit Log"],
      icon: (
        <svg className="h-6 w-6 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.75}
            d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
          />
        </svg>
      ),
    },
  ];

  return (
    <div id="pillars" className="mt-12">
      <div className="text-center sm:text-left">
        <h2 className="text-2xl font-bold tracking-tight text-white sm:text-3xl">
          Core Architectural Pillars
        </h2>
        <p className="mt-2 text-sm text-slate-400 max-w-2xl">
          Engineered to satisfy the requirements of PERFORMai-360: grounding, explainability, stateful orchestration, and human accountability.
        </p>
      </div>

      <div className="mt-8 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {pillars.map((pillar, idx) => (
          <div
            key={idx}
            className="glass-panel glass-panel-hover flex flex-col justify-between rounded-2xl p-6"
          >
            <div>
              <div className="flex items-center justify-between">
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-slate-900 border border-slate-800">
                  {pillar.icon}
                </div>
                <span
                  className={`rounded-full border px-2.5 py-0.5 text-xs font-semibold ${pillar.badgeColor}`}
                >
                  {pillar.badge}
                </span>
              </div>

              <h3 className="mt-5 text-base font-bold text-white">{pillar.title}</h3>
              <p className="text-xs font-medium text-indigo-400 mt-0.5">{pillar.tagline}</p>
              <p className="mt-3 text-xs leading-relaxed text-slate-400">{pillar.description}</p>
            </div>

            <div className="mt-6 pt-4 border-t border-slate-800/80">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 block mb-2">
                Key Capabilities
              </span>
              <ul className="space-y-1.5">
                {pillar.specs.map((spec, sIdx) => (
                  <li key={sIdx} className="flex items-center text-xs text-slate-300">
                    <span className="mr-2 h-1.5 w-1.5 rounded-full bg-indigo-500"></span>
                    {spec}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
