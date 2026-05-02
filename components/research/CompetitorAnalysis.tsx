import type { CompetitorLevel, CompetitorRow } from "./types";

type CompetitorAnalysisProps = {
  competitors: CompetitorRow[];
  isLoading?: boolean;
  error?: string;
};

const headers = [
  "Имя / бренд",
  "Площадка",
  "Уровень",
  "Позиционирование",
  "Сегмент аудитории",
  "Главное обещание",
  "Чем выделяется",
  "Продукты конкурента",
  "Цены",
  "Лид-магниты",
  "Воронка",
  "Instagram: максимум просмотров",
];

const levelStyles: Record<CompetitorLevel, string> = {
  Крупный: "border-blue-200 bg-blue-50 text-blue-700",
  Средний: "border-violet-200 bg-violet-50 text-violet-700",
  Нишевый: "border-emerald-200 bg-emerald-50 text-emerald-700",
  Дополнительный: "border-amber-200 bg-amber-50 text-amber-700",
};

const cellClass =
  "min-w-[190px] border-b border-slate-200/80 px-4 py-4 align-top text-sm leading-6 text-slate-700";
const headerClass =
  "sticky top-0 z-10 min-w-[190px] border-b border-slate-200 bg-slate-50/95 px-4 py-3 text-left text-xs font-semibold uppercase tracking-[0.12em] text-slate-500 backdrop-blur";

export default function CompetitorAnalysis({ competitors, isLoading, error }: CompetitorAnalysisProps) {
  return (
    <section className="overflow-hidden rounded-[28px] border border-white/70 bg-white/85 shadow-[0_24px_70px_rgba(15,23,42,0.10)] backdrop-blur-xl">
      <div className="flex flex-col gap-5 p-5 sm:p-7 lg:p-8">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-3">
              <span className="rounded-full border border-slate-200 bg-slate-950 px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-white">
                Competitor Analysis
              </span>
              <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-500">
                Live web search
              </span>
            </div>
            <div>
              <h2 className="text-3xl font-semibold tracking-[-0.03em] text-slate-950">
                Карта конкурентного поля
              </h2>
              <p className="mt-2 max-w-2xl text-base leading-7 text-slate-600">
                Отдельный веб-поиск собирает 10 конкурентов и раскладывает рынок по уровню, обещанию,
                продуктам, ценам, воронке и Instagram-контенту.
              </p>
            </div>
          </div>

          {competitors.length > 0 ? (
            <div className="grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">
              {(["Крупный", "Средний", "Нишевый", "Дополнительный"] as CompetitorLevel[]).map((level) => (
                <div key={level} className="rounded-2xl border border-slate-200 bg-white px-3 py-2 shadow-sm">
                  <p className="text-xs text-slate-400">{level}</p>
                  <p className="font-semibold text-slate-950">
                    {competitors.filter((competitor) => competitor.level === level).length}
                  </p>
                </div>
              ))}
            </div>
          ) : null}
        </div>

        {isLoading ? (
          <div className="rounded-2xl border border-blue-100 bg-blue-50 px-4 py-3 text-sm font-medium text-blue-700">
            <span className="mr-2 inline-block h-2 w-2 animate-pulse rounded-full bg-blue-500" />
            Ищу конкурентов через веб-поиск...
          </div>
        ) : null}

        {error ? (
          <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700">
            {error}
          </div>
        ) : null}

        {competitors.length > 0 ? (
          <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm">
            <table className="w-full min-w-[2200px] border-collapse">
              <thead>
                <tr>
                  {headers.map((header) => (
                    <th key={header} className={headerClass}>
                      {header}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {competitors.map((competitor, index) => (
                  <tr key={competitor.id} className={index % 2 === 0 ? "bg-white" : "bg-slate-50/70"}>
                    <td className="min-w-[210px] border-b border-slate-200/80 px-4 py-4 align-top">
                      <p className="font-semibold text-slate-950">{competitor.name}</p>
                    </td>
                    <td className={cellClass}>{competitor.platform}</td>
                    <td className="min-w-[150px] border-b border-slate-200/80 px-4 py-4 align-top">
                      <span
                        className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${levelStyles[competitor.level]}`}
                      >
                        {competitor.level}
                      </span>
                    </td>
                    <td className={cellClass}>{competitor.positioning}</td>
                    <td className={cellClass}>{competitor.audienceSegment}</td>
                    <td className={cellClass}>{competitor.mainPromise}</td>
                    <td className={cellClass}>{competitor.differentiator}</td>
                    <td className={cellClass}>{competitor.products}</td>
                    <td className={cellClass}>{competitor.prices}</td>
                    <td className={cellClass}>{competitor.leadMagnets}</td>
                    <td className={cellClass}>{competitor.funnel}</td>
                    <td className={cellClass}>{competitor.instagramContent}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </div>
    </section>
  );
}
