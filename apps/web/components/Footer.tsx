"use client";

import React from "react";

export function Footer() {
  return (
    <footer className="mt-20 border-t border-slate-900 bg-slate-950/80 py-10">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col items-center justify-between gap-6 sm:flex-row">
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-base font-bold text-white">PERFORMai-360</span>
              <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] font-mono text-slate-400">
                v0.1.0 (Phase 1)
              </span>
            </div>
            <p className="mt-1 text-xs text-slate-500">
              AI-Driven Bias-Aware 360° Performance Evaluation for Software Engineering Teams
            </p>
          </div>

          <div className="flex items-center space-x-6 text-xs text-slate-400">
            <span className="text-slate-500">Stack: Next.js 16 • FastAPI • PostgreSQL 16 • LangGraph</span>
          </div>
        </div>

        {/* Ethical Guardrail Disclaimer */}
        <div className="mt-8 rounded-xl border border-slate-800/80 bg-slate-900/40 p-4 text-xs text-slate-400">
          <p className="font-semibold text-slate-300">
            Ethical Governance & Decision-Support Principle (PRD Section 1 & 3):
          </p>
          <p className="mt-1 text-slate-400 leading-relaxed">
            PERFORMai-360 is strictly an assistive decision-support intelligence platform. It organizes evidence, extracts relevant contributions, flags potential review-period imbalances, and drafts review reports for human review. It does not and must not make autonomous employment decisions, including promotions, salary adjustments, hiring, or terminations. Human managers retain full authority and accountability for all finalized evaluations.
          </p>
        </div>

        <div className="mt-6 text-center text-xs text-slate-600">
          © 2026 PERFORMai-360 Team. Developed with Antigravity IDE.
        </div>
      </div>
    </footer>
  );
}
