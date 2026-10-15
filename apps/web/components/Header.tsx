"use client";

import React from "react";

export function Header() {
  return (
    <header className="sticky top-0 z-50 border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6 lg:px-8">
        {/* Brand */}
        <div className="flex items-center space-x-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-purple-500 shadow-md shadow-indigo-500/20">
            <svg
              className="h-6 w-6 text-white"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
              />
            </svg>
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-xl font-bold tracking-tight text-white">
                PERFORM<span className="text-indigo-400">ai</span>
                <span className="text-purple-400">-360</span>
              </span>
              <span className="rounded-full border border-indigo-500/30 bg-indigo-500/10 px-2 py-0.5 text-xs font-semibold text-indigo-300">
                Phase 1 Foundation
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Bias-Aware 360° Evaluation Intelligence for Engineering Teams
            </p>
          </div>
        </div>

        {/* Navigation links */}
        <nav className="hidden items-center space-x-6 md:flex">
          <a
            href="#overview"
            className="text-sm font-medium text-slate-300 transition-colors hover:text-white"
          >
            Overview
          </a>
          <a
            href="#health"
            className="text-sm font-medium text-slate-300 transition-colors hover:text-white"
          >
            Health Probes
          </a>
          <a
            href="#pillars"
            className="text-sm font-medium text-slate-300 transition-colors hover:text-white"
          >
            Core Architecture
          </a>
          <a
            href="#roadmap"
            className="text-sm font-medium text-slate-300 transition-colors hover:text-white"
          >
            Roadmap
          </a>
        </nav>

        {/* Status Indicator */}
        <div className="flex items-center space-x-2">
          <div className="flex items-center space-x-1.5 rounded-lg border border-slate-800 bg-slate-900/90 px-3 py-1.5 text-xs text-slate-300">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500"></span>
            </span>
            <span className="font-mono">Local Dev</span>
          </div>
        </div>
      </div>
    </header>
  );
}
