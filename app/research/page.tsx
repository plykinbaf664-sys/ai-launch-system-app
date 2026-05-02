'use client';

import { useState } from "react";

import ReviewsTable from "@/components/ReviewsTable";

export type WorkflowStatus = {
  stage: "idle" | "reviews" | "competitors" | "patterns" | "done" | "error";
  label: string;
  detail: string;
};

const idleStatus: WorkflowStatus = {
  stage: "idle",
  label: "Готов к запуску",
  detail: "Введите нишу и аудиторию, чтобы начать исследование.",
};

const steps = [
  { key: "reviews", label: "Отзывы" },
  { key: "competitors", label: "Конкуренты" },
  { key: "patterns", label: "Стратегия" },
] as const;

function isStepActive(status: WorkflowStatus["stage"], step: (typeof steps)[number]["key"]) {
  if (status === "done") {
    return true;
  }

  if (status === "error") {
    return false;
  }

  const order = steps.findIndex((item) => item.key === step);
  const current = steps.findIndex((item) => item.key === status);

  return current >= order;
}

export default function ResearchPage() {
  const [workflowStatus, setWorkflowStatus] = useState<WorkflowStatus>(idleStatus);
  const isRunning = ["reviews", "competitors", "patterns"].includes(workflowStatus.stage);

  return (
    <main className="min-h-screen overflow-hidden bg-[#f5f7fb] text-slate-950">
      <div className="pointer-events-none absolute inset-0 -z-0 bg-[linear-gradient(rgba(15,23,42,0.035)_1px,transparent_1px),linear-gradient(90deg,rgba(15,23,42,0.035)_1px,transparent_1px)] bg-[size:36px_36px]" />
      <div className="pointer-events-none absolute left-1/2 top-0 -z-0 h-[420px] w-[760px] -translate-x-1/2 rounded-full bg-[radial-gradient(circle,rgba(59,130,246,0.18),rgba(14,165,233,0.08)_42%,transparent_72%)] blur-3xl" />

      <div className="relative z-10 mx-auto flex w-full max-w-[1480px] flex-col gap-10 px-4 py-6 sm:px-6 lg:px-8 lg:py-10">
        <section className="overflow-hidden rounded-[28px] border border-white/70 bg-white/75 shadow-[0_24px_80px_rgba(15,23,42,0.10)] backdrop-blur-xl">
          <div className="grid gap-8 p-6 sm:p-8 lg:grid-cols-[1.15fr_0.85fr] lg:p-10">
            <div className="flex flex-col justify-between gap-12">
              <div className="space-y-6">
                <span className="inline-flex w-fit items-center rounded-full border border-slate-200 bg-slate-950 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-white shadow-sm">
                  AI-first market intelligence
                </span>
                <div className="space-y-4">
                  <h1 className="max-w-4xl text-5xl font-semibold tracking-[-0.04em] text-slate-950 sm:text-6xl lg:text-7xl">
                    БАЗОВАЯ БАЗА
                  </h1>
                  <p className="max-w-2xl text-lg leading-8 text-slate-600 sm:text-xl">
                    Собирает отзывы, анализирует конкурентов и превращает это в маркетинговую стратегию в 1 клик.
                  </p>
                </div>
              </div>

              <div className="grid max-w-3xl gap-3 sm:grid-cols-3">
                {["Отзывы", "Конкуренты", "Стратегия"].map((item) => (
                  <div
                    key={item}
                    className="rounded-2xl border border-slate-200/80 bg-white/70 px-4 py-3 shadow-sm"
                  >
                    <p className="text-xs font-medium uppercase tracking-[0.16em] text-slate-400">
                      Module
                    </p>
                    <p className="mt-1 text-sm font-semibold text-slate-900">{item}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="relative min-h-[320px] overflow-hidden rounded-3xl border border-slate-200 bg-slate-950 p-6 text-white shadow-[0_18px_60px_rgba(15,23,42,0.25)]">
              <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.07)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.07)_1px,transparent_1px)] bg-[size:28px_28px] opacity-40" />
              <div className="absolute -right-24 -top-24 h-64 w-64 rounded-full bg-cyan-400/20 blur-3xl" />
              <div className="absolute -bottom-28 left-8 h-64 w-64 rounded-full bg-blue-500/20 blur-3xl" />
              <div className="relative flex h-full flex-col justify-between gap-10">
                <div className="flex items-center justify-between">
                  <span className="rounded-full bg-white/10 px-3 py-1 text-xs font-medium text-white/80">
                    Workflow monitor
                  </span>
                  <span
                    className={`h-2.5 w-2.5 rounded-full ${
                      isRunning
                        ? "animate-pulse bg-cyan-300 shadow-[0_0_24px_rgba(103,232,249,0.9)]"
                        : workflowStatus.stage === "error"
                          ? "bg-red-400 shadow-[0_0_24px_rgba(248,113,113,0.9)]"
                          : "bg-emerald-400 shadow-[0_0_24px_rgba(52,211,153,0.9)]"
                    }`}
                  />
                </div>

                <div className="space-y-5">
                  <div className="rounded-2xl border border-white/10 bg-white/10 p-4 backdrop-blur">
                    <p className="text-sm text-white/60">Текущий этап</p>
                    <p className="mt-1 text-2xl font-semibold tracking-[-0.02em]">
                      {workflowStatus.label}
                    </p>
                    <p className="mt-2 text-sm leading-6 text-white/60">{workflowStatus.detail}</p>
                  </div>

                  <div className="grid gap-3">
                    {steps.map((step) => {
                      const active = isStepActive(workflowStatus.stage, step.key);
                      const current = workflowStatus.stage === step.key;

                      return (
                        <div key={step.key} className="flex items-center gap-3">
                          <span
                            className={`flex h-8 w-8 items-center justify-center rounded-full border text-xs font-semibold ${
                              active
                                ? "border-cyan-300/60 bg-cyan-300/20 text-cyan-100"
                                : "border-white/10 bg-white/5 text-white/35"
                            }`}
                          >
                            {current ? <span className="h-2 w-2 animate-ping rounded-full bg-cyan-200" /> : active ? "✓" : ""}
                          </span>
                          <div className="min-w-0 flex-1">
                            <p className={active ? "text-sm font-semibold text-white" : "text-sm text-white/40"}>
                              {step.label}
                            </p>
                            <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-white/10">
                              <div
                                className={`h-full rounded-full transition-all duration-500 ${
                                  active ? "w-full bg-cyan-300" : "w-0 bg-cyan-300"
                                }`}
                              />
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <ReviewsTable onWorkflowStatusChange={setWorkflowStatus} />
      </div>
    </main>
  );
}
