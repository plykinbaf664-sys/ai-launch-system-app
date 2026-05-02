import type { ReactNode } from "react";

import type { CompetitorRow, ReviewRow } from "./types";

type PatternAnalyzerProps = {
  niche: string;
  positioning: string;
  reviews: ReviewRow[];
  competitors: CompetitorRow[];
};

function compactList(values: string[], limit = 3) {
  return values
    .map((value) => value.trim())
    .filter((value) => value.length > 20)
    .slice(0, limit);
}

function ReportBlock({
  title,
  label,
  children,
}: {
  title: string;
  label: string;
  children: ReactNode;
}) {
  return (
    <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-blue-600">{label}</p>
      <h3 className="mt-2 text-xl font-semibold tracking-[-0.02em] text-slate-950">{title}</h3>
      <div className="mt-4 text-sm leading-7 text-slate-700">{children}</div>
    </section>
  );
}

export default function PatternAnalyzer({
  niche,
  positioning,
  reviews,
  competitors,
}: PatternAnalyzerProps) {
  const pains = compactList(reviews.map((review) => review.pains));
  const fears = compactList(reviews.map((review) => review.fears));
  const desired = compactList(reviews.map((review) => review.idealResult));
  const expectations = compactList(reviews.map((review) => review.expectations));
  const triedBefore = compactList(reviews.map((review) => review.triedBefore));
  const promises = compactList(competitors.map((competitor) => competitor.mainPromise));
  const differentiators = compactList(competitors.map((competitor) => competitor.differentiator));
  const funnels = compactList(competitors.map((competitor) => competitor.funnel));

  return (
    <section className="overflow-hidden rounded-[28px] border border-white/70 bg-slate-950 text-white shadow-[0_28px_90px_rgba(15,23,42,0.22)]">
      <div className="relative p-5 sm:p-7 lg:p-8">
        <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.045)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.045)_1px,transparent_1px)] bg-[size:34px_34px] opacity-50" />
        <div className="absolute -right-28 -top-28 h-80 w-80 rounded-full bg-blue-500/20 blur-3xl" />
        <div className="absolute -bottom-28 left-10 h-80 w-80 rounded-full bg-cyan-400/10 blur-3xl" />

        <div className="relative grid gap-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="space-y-3">
              <span className="inline-flex rounded-full border border-white/15 bg-white/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-white/80">
                Pattern Analyzer
              </span>
              <div>
                <h2 className="text-3xl font-semibold tracking-[-0.03em] text-white">
                  Аналитический отчет по рынку
                </h2>
                <p className="mt-2 max-w-3xl text-base leading-7 text-white/65">
                  Блок не делает веб-поиск. Он превращает данные Research Reviews и Competitor Analysis
                  в позиционирование, CJM, продуктовую линейку и денежную воронку.
                </p>
              </div>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/10 px-4 py-3 text-sm text-white/70 backdrop-blur">
              <span className="font-semibold text-white">{reviews.length}</span> отзывов ·{" "}
              <span className="font-semibold text-white">{competitors.length}</span> конкурентов
            </div>
          </div>

          <div className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
            <ReportBlock label="Positioning" title="Четкое позиционирование эксперта">
              <p className="m-0">
                {positioning}. Упаковку стоит привязать к нише {niche}: показать конкретную ситуацию
                клиента, обещать измеримый результат и сразу снять главный риск покупки.
              </p>
            </ReportBlock>

            <ReportBlock label="Differentiation" title="Отстройка от конкурентов">
              <p className="m-0">
                На рынке часто обещают: {promises[0] || "быстрый результат"}. Выделение стоит строить на
                точной диагностике, языке клиента и доказательстве отличия:{" "}
                {differentiators[0] || "методология, кейсы и понятный первый шаг"}.
              </p>
            </ReportBlock>
          </div>

          <div className="grid gap-4 lg:grid-cols-3">
            <ReportBlock label="Segments" title="3 горячих сегмента ЦА">
              <ol className="m-0 list-decimal space-y-2 pl-5">
                <li>Клиенты с острой болью: {pains[0] || "уже понимают проблему и ищут быстрый первый шаг"}.</li>
                <li>Клиенты с высоким ожиданием результата: {desired[0] || "хотят понятный, измеримый итог"}.</li>
                <li>Клиенты после неудачных попыток: {triedBefore[0] || "уже пробовали решать задачу и готовы платить за систему"}.</li>
              </ol>
            </ReportBlock>

            <ReportBlock label="Product" title="Линейка продуктов">
              <p className="m-0">
                Диагностика → короткий интенсив → групповая программа → личное сопровождение → клуб
                поддержки. Главный фокус: {expectations[0] || "понятный план, поддержка и измеримый прогресс"}.
              </p>
            </ReportBlock>

            <ReportBlock label="AI leverage" title="AI-усиление продуктов">
              <p className="m-0">
                Диагностика через AI-анкету, интенсив с персональными заданиями, программа с AI-трекером,
                сопровождение со сводками, напоминаниями и анализом препятствий клиента.
              </p>
            </ReportBlock>
          </div>

          <div className="grid gap-4 lg:grid-cols-[0.95fr_1.05fr]">
            <ReportBlock label="CJM" title="CJM и эмоции клиента">
              <ol className="m-0 list-decimal space-y-2 pl-5">
                <li>Осознание проблемы: тревога и усталость. Триггер: {pains[0] || "боль мешает повседневной жизни"}.</li>
                <li>Поиск решений: надежда и скепсис. Клиент сравнивает обещания, цены, отзывы и формат.</li>
                <li>Проверка доверия: осторожность. Важны кейсы, метод и понятный первый шаг.</li>
                <li>Покупка: страх ошибиться. Нужны прозрачная программа и снятие риска.</li>
                <li>Прохождение продукта: облегчение или сопротивление. Нужен видимый прогресс.</li>
              </ol>
            </ReportBlock>

            <ReportBlock label="Revenue funnel" title="Воронка, чтобы это приносило деньги">
              <p className="m-0">
                Базовая связка: {funnels[0] || "контент → лид-магнит → прогрев → созвон/вебинар → основной продукт"}.
                Усилить ее стоит контентом на боли, страхи и предрассудки:{" "}
                {fears[0] || "страх ошибки, потери денег и отсутствия результата"}.
              </p>
            </ReportBlock>
          </div>
        </div>
      </div>
    </section>
  );
}
