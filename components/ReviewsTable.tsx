'use client';

import { FormEvent, useState } from "react";

import CompetitorAnalysis from "@/components/research/CompetitorAnalysis";
import PatternAnalyzer from "@/components/research/PatternAnalyzer";
import type { CompetitorRow, ReviewRow } from "@/components/research/types";
import type { WorkflowStatus } from "@/app/research/page";

type ReviewsResponse = {
  niche: string;
  positioning: string;
  reviews: ReviewRow[];
};

type ReviewsErrorResponse = {
  error?: string;
};

type CompetitorsResponse = {
  competitors: CompetitorRow[];
};

type ReviewsTableProps = {
  onWorkflowStatusChange?: (status: WorkflowStatus) => void;
};

const tableHeaders = [
  "Ситуация клиента",
  "Идеальный результат",
  "Ожидания",
  "Оправдания почему нет результата",
  "Страхи",
  "Боли",
  "Предрассудки",
  "Что уже пробовал",
];

const cellClass =
  "min-w-[220px] border-b border-slate-200/80 px-4 py-4 align-top text-sm leading-6 text-slate-700";
const headerClass =
  "sticky top-0 z-10 min-w-[220px] border-b border-slate-200 bg-slate-50/95 px-4 py-3 text-left text-xs font-semibold uppercase tracking-[0.12em] text-slate-500 backdrop-blur";

function escapeCsvValue(value: string) {
  return `"${value.replaceAll('"', '""')}"`;
}

export default function ReviewsTable({ onWorkflowStatusChange }: ReviewsTableProps) {
  const [niche, setNiche] = useState("");
  const [positioning, setPositioning] = useState("");
  const [reviews, setReviews] = useState<ReviewRow[]>([]);
  const [competitors, setCompetitors] = useState<CompetitorRow[]>([]);
  const [error, setError] = useState("");
  const [competitorError, setCompetitorError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isCompetitorsLoading, setIsCompetitorsLoading] = useState(false);
  const [lastSearch, setLastSearch] = useState<{ niche: string; positioning: string } | null>(null);

  async function loadCompetitors(searchNiche: string, searchPositioning: string, sourceReviews: ReviewRow[]) {
    setCompetitors([]);
    setCompetitorError("");
    setIsCompetitorsLoading(true);
    onWorkflowStatusChange?.({
      stage: "competitors",
      label: "Анализируем конкурентов",
      detail: "Система ищет крупных, средних и нишевых игроков через веб-поиск.",
    });

    try {
      const response = await fetch("/api/research-competitors", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          niche: searchNiche,
          positioning: searchPositioning,
          reviews: sourceReviews,
        }),
      });

      const data = (await response.json()) as CompetitorsResponse | ReviewsErrorResponse;

      if (!response.ok || !("competitors" in data)) {
        const errorMessage = "error" in data ? data.error : undefined;
        throw new Error(errorMessage || "Не удалось собрать конкурентов.");
      }

      setCompetitors(data.competitors);
      onWorkflowStatusChange?.({
        stage: "patterns",
        label: "Собираем стратегию",
        detail: "Pattern Analyzer соединяет отзывы и конкурентов без дополнительного веб-поиска.",
      });
      window.setTimeout(() => {
        onWorkflowStatusChange?.({
          stage: "done",
          label: "Исследование готово",
          detail: "Отзывы, конкуренты и стратегический отчет собраны.",
        });
      }, 500);
    } catch (loadError) {
      const message =
        loadError instanceof Error ? loadError.message : "Произошла ошибка при сборе конкурентов.";
      setCompetitorError(message);
      onWorkflowStatusChange?.({
        stage: "error",
        label: "Конкуренты не собраны",
        detail: message,
      });
    } finally {
      setIsCompetitorsLoading(false);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setCompetitorError("");
    setCompetitors([]);
    setIsLoading(true);
    onWorkflowStatusChange?.({
      stage: "reviews",
      label: "Ищем отзывы",
      detail: "Система собирает живые first-person источники через веб-поиск.",
    });

    try {
      const response = await fetch("/api/research-reviews", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          niche: niche.trim(),
          positioning: positioning.trim(),
        }),
      });

      const data = (await response.json()) as ReviewsResponse | ReviewsErrorResponse;

      if (!response.ok || !("reviews" in data)) {
        const errorMessage = "error" in data ? data.error : undefined;
        throw new Error(errorMessage || "Не удалось собрать отзывы.");
      }

      setReviews(data.reviews);
      setLastSearch({
        niche: data.niche,
        positioning: data.positioning,
      });
      void loadCompetitors(data.niche, data.positioning, data.reviews);
    } catch (submitError) {
      const message =
        submitError instanceof Error ? submitError.message : "Произошла ошибка при сборе отзывов.";
      setError(message);
      setReviews([]);
      setCompetitors([]);
      onWorkflowStatusChange?.({
        stage: "error",
        label: "Отзывы не собраны",
        detail: message,
      });
    } finally {
      setIsLoading(false);
    }
  }

  function handleDownloadCsv() {
    if (reviews.length === 0) {
      return;
    }

    const headers = ["Источник", "Ссылка", ...tableHeaders];

    const rows = reviews.map((review) =>
      [
        review.sourceLabel,
        review.sourceUrl,
        review.clientSituation,
        review.idealResult,
        review.expectations,
        review.whyNoResult,
        review.fears,
        review.pains,
        review.prejudices,
        review.triedBefore,
      ]
        .map(escapeCsvValue)
        .join(","),
    );

    const csvContent = "\uFEFF" + [headers.join(","), ...rows].join("\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    const safeNiche = (lastSearch?.niche || "research").replaceAll(/\s+/g, "-").toLowerCase();

    link.href = url;
    link.download = `${safeNiche}-reviews.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  return (
    <div className="grid gap-8">
      <section className="overflow-hidden rounded-[28px] border border-white/70 bg-white/85 shadow-[0_24px_70px_rgba(15,23,42,0.10)] backdrop-blur-xl">
        <div className="grid gap-8 p-5 sm:p-7 lg:grid-cols-[0.9fr_1.1fr] lg:p-8">
          <div className="space-y-5">
            <div className="flex flex-wrap items-center gap-3">
              <span className="rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-blue-700">
                Research Reviews
              </span>
              <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-500">
                Web search
              </span>
            </div>
            <div className="space-y-3">
              <h2 className="text-3xl font-semibold tracking-[-0.03em] text-slate-950">
                Определяем точки кипения клиентов
              </h2>
              <p className="max-w-xl text-base leading-7 text-slate-600">
                Введите нишу и кому вы помогаете. Система соберет живые источники и разложит рынок на
                ситуации, боли, страхи и ожидания.
              </p>
            </div>

            {lastSearch ? (
              <div className="grid gap-3 rounded-2xl border border-slate-200 bg-slate-50/80 p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
                  Последний прогон
                </p>
                <p className="text-sm text-slate-700">
                  <span className="font-semibold text-slate-950">Ниша:</span> {lastSearch.niche}
                </p>
                <p className="text-sm text-slate-700">
                  <span className="font-semibold text-slate-950">Кому я помогаю:</span>{" "}
                  {lastSearch.positioning}
                </p>
                <p className="text-sm text-slate-700">
                  <span className="font-semibold text-slate-950">Источников:</span> {reviews.length}
                </p>
              </div>
            ) : null}
          </div>

          <form onSubmit={handleSubmit} className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
            <div className="grid gap-4">
              <label className="grid gap-2">
                <span className="text-sm font-semibold text-slate-800">Ниша</span>
                <input
                  value={niche}
                  onChange={(event) => setNiche(event.target.value)}
                  placeholder="Например: онлайн-фитнес для женщин 35+"
                  required
                  className="min-h-12 rounded-2xl border border-slate-200 bg-slate-50 px-4 text-base text-slate-950 outline-none transition focus:border-blue-400 focus:bg-white focus:ring-4 focus:ring-blue-100"
                />
              </label>

              <label className="grid gap-2">
                <span className="text-sm font-semibold text-slate-800">Кому я помогаю</span>
                <textarea
                  value={positioning}
                  onChange={(event) => setPositioning(event.target.value)}
                  placeholder="Например: помогаю женщинам после развода вернуть опору и снизить тревогу"
                  required
                  rows={4}
                  className="min-h-32 resize-y rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-base leading-7 text-slate-950 outline-none transition focus:border-blue-400 focus:bg-white focus:ring-4 focus:ring-blue-100"
                />
              </label>

              <div className="flex flex-wrap gap-3 pt-1">
                <button
                  type="submit"
                  disabled={isLoading}
                  className="inline-flex min-h-12 items-center justify-center rounded-2xl bg-slate-950 px-5 text-sm font-semibold text-white shadow-[0_14px_30px_rgba(15,23,42,0.18)] transition hover:-translate-y-0.5 hover:bg-slate-800 disabled:translate-y-0 disabled:cursor-not-allowed disabled:bg-slate-400 disabled:shadow-none"
                >
                  {isLoading ? (
                    <span className="inline-flex items-center gap-2">
                      <span className="h-2 w-2 animate-pulse rounded-full bg-white" />
                      Собираю сигналы...
                    </span>
                  ) : (
                    "Собрать 10 источников"
                  )}
                </button>

                <button
                  type="button"
                  onClick={handleDownloadCsv}
                  disabled={reviews.length === 0}
                  className="inline-flex min-h-12 items-center justify-center rounded-2xl border border-slate-200 bg-white px-5 text-sm font-semibold text-slate-800 transition hover:-translate-y-0.5 hover:border-slate-300 hover:shadow-sm disabled:translate-y-0 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400 disabled:shadow-none"
                >
                  Скачать CSV
                </button>
              </div>
            </div>
          </form>
        </div>

        {error ? (
          <div className="mx-5 mb-5 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700 sm:mx-7 lg:mx-8">
            {error}
          </div>
        ) : null}

        {reviews.length > 0 ? (
          <div className="border-t border-slate-200 bg-white/70 p-3 sm:p-4 lg:p-5">
            <div className="mb-4 flex flex-wrap items-end justify-between gap-3 px-1">
              <div>
                <h3 className="text-lg font-semibold text-slate-950">Research Reviews</h3>
                <p className="mt-1 text-sm text-slate-500">
                  Длинные цитаты сохраняются, таблица прокручивается горизонтально.
                </p>
              </div>
              <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">
                {reviews.length} источников
              </span>
            </div>
            <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm">
              <table className="w-full min-w-[1500px] border-collapse">
                <thead>
                  <tr>
                    {tableHeaders.map((title) => (
                      <th key={title} className={headerClass}>
                        {title}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {reviews.map((review, index) => (
                    <tr key={review.id} className={index % 2 === 0 ? "bg-white" : "bg-slate-50/70"}>
                      <td className={cellClass}>{review.clientSituation}</td>
                      <td className={cellClass}>{review.idealResult}</td>
                      <td className={cellClass}>{review.expectations}</td>
                      <td className={cellClass}>{review.whyNoResult}</td>
                      <td className={cellClass}>{review.fears}</td>
                      <td className={cellClass}>{review.pains}</td>
                      <td className={cellClass}>{review.prejudices}</td>
                      <td className={cellClass}>{review.triedBefore}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : null}
      </section>

      {reviews.length > 0 && lastSearch ? (
        <>
          <CompetitorAnalysis
            competitors={competitors}
            error={competitorError}
            isLoading={isCompetitorsLoading}
          />
          {competitors.length > 0 ? (
            <PatternAnalyzer
              niche={lastSearch.niche}
              positioning={lastSearch.positioning}
              reviews={reviews}
              competitors={competitors}
            />
          ) : null}
        </>
      ) : null}
    </div>
  );
}
