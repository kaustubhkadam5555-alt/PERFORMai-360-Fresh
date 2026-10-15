"use client";

import React from "react";
import { Header } from "../components/Header";
import { BackendHealthCard } from "../components/BackendHealthCard";
import { ReviewAnalysisCard } from "../components/ReviewAnalysisCard";
import { AuditReviewCard } from "../components/AuditReviewCard";
import { PillarCards } from "../components/PillarCards";
import { PhaseRoadmap } from "../components/PhaseRoadmap";
import { Footer } from "../components/Footer";

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col bg-slate-950">
      <Header />

      <main className="flex-1">
        {/* Hero Section */}
        <section id="overview" className="relative overflow-hidden py-12 sm:py-16 lg:py-20">
          {/* Subtle background glow */}
          <div className="pointer-events-none absolute -top-40 left-1/2 -z-10 h-[500px] w-[800px] -translate-x-1/2 bg-gradient-to-tr from-indigo-600/15 via-purple-600/15 to-cyan-500/10 blur-3xl" />

          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <div className="text-center">
              {/* Badge */}
              <div className="inline-flex items-center space-x-2 rounded-full border border-indigo-500/30 bg-indigo-500/10 px-3.5 py-1.5 text-xs font-semibold text-indigo-300">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                <span>Phase 6 — Deterministic Bias &amp; Evidence-Quality Audit Engine Live</span>
              </div>

              {/* Headline */}
              <h1 className="mt-6 text-4xl font-extrabold tracking-tight text-white sm:text-5xl lg:text-6xl">
                AI-Driven <span className="bg-gradient-to-r from-indigo-400 via-purple-400 to-pink-400 bg-clip-text text-transparent">Bias-Aware</span> 360° Evaluation
              </h1>

              {/* Subtitle */}
              <p className="mx-auto mt-5 max-w-3xl text-base text-slate-300 sm:text-lg sm:leading-relaxed">
                Empowering software engineering leaders to prepare evidence-grounded, balanced, and explainable 360-degree performance reviews with deterministic audit checks and mandatory human approval.
              </p>

              {/* Metrics / Key Guarantees Bar */}
              <div className="mt-10 grid grid-cols-2 gap-4 sm:grid-cols-4 max-w-4xl mx-auto">
                <div className="glass-panel rounded-xl p-4 text-center border border-slate-800">
                  <span className="block text-2xl font-extrabold text-white sm:text-3xl">360°</span>
                  <span className="text-xs font-medium text-slate-400 mt-1 block">Self, Peer, & Manager Evidence</span>
                </div>
                <div className="glass-panel rounded-xl p-4 text-center border border-slate-800">
                  <span className="block text-2xl font-extrabold text-indigo-400 sm:text-3xl">5 Rules</span>
                  <span className="text-xs font-medium text-slate-400 mt-1 block">Deterministic Bias Audits</span>
                </div>
                <div className="glass-panel rounded-xl p-4 text-center border border-slate-800">
                  <span className="block text-2xl font-extrabold text-purple-400 sm:text-3xl">4 Agents</span>
                  <span className="text-xs font-medium text-slate-400 mt-1 block">LangGraph State Machine</span>
                </div>
                <div className="glass-panel rounded-xl p-4 text-center border border-slate-800">
                  <span className="block text-2xl font-extrabold text-emerald-400 sm:text-3xl">100%</span>
                  <span className="text-xs font-medium text-slate-400 mt-1 block">Human Approval Required</span>
                </div>
              </div>
            </div>

            {/* Live Health Probe Card */}
            <div className="mt-14">
              <BackendHealthCard />
            </div>

            {/* Phase 5: AI Review Analysis Interface */}
            <ReviewAnalysisCard />

            {/* Phase 6: Deterministic Bias & Evidence-Quality Audit Interface */}
            <AuditReviewCard />

            {/* Core Architectural Pillars */}
            <PillarCards />

            {/* Phased Roadmap */}
            <PhaseRoadmap />
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}
