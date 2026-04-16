'use client';

import { FormEvent, useState } from "react";

type ReviewRow = {
  id: string;
  sourceLabel: string;
  sourceUrl: string;
  problem: string;
  whyNoResult: string;
  fears: string;
  desiredResult: string;
  question: string;
};

type ReviewsResponse = {
  niche: string;
  positioning: string;
  reviews: ReviewRow[];
};

const tableHeaders = [
  "Источник",
  "Проблема",
  "Почему до сих пор нет результата",
  "Страхи",
  "Желаемый результат",
  "Вопрос при покупке",
];

const cellStyle = {
  border: "1px solid #d1d5db",
  padding: "12px",
  verticalAlign: "top" as const,
  whiteSpace: "pre-wrap" as const,
  lineHeight: 1.6,
};

function escapeCsvValue(value: string) {
  return `"${value.replaceAll('"', '""')}"`;
}

export default function HypothesisCard() {
  const [niche, setNiche] = useState("");
  const [positioning, setPositioning] = useState("");
  const [reviews, setReviews] = useState<ReviewRow[]>([]);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [lastSearch, setLastSearch] = useState<{ niche: string; positioning: string } | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setIsLoading(true);

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

      const data = (await response.json()) as ReviewsResponse | { error?: string };

      if (!response.ok || !("reviews" in data)) {
        throw new Error(data.error || "Не удалось собрать отзывы.");
      }

      setReviews(data.reviews);
      setLastSearch({
        niche: data.niche,
        positioning: data.positioning,
      });
    } catch (submitError) {
      const message =
        submitError instanceof Error ? submitError.message : "Произошла ошибка при сборе отзывов.";
      setError(message);
      setReviews([]);
    } finally {
      setIsLoading(false);
    }
  }

  function handleDownloadCsv() {
    if (reviews.length === 0) {
      return;
    }

    const headers = ["Источник", "Ссылка", ...tableHeaders.slice(1)];

    const rows = reviews.map((review) =>
      [
        review.sourceLabel,
        review.sourceUrl,
        review.problem,
        review.whyNoResult,
        review.fears,
        review.desiredResult,
        review.question,
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
    <section
      style={{
        border: "1px solid #d1d5db",
        borderRadius: "16px",
        padding: "24px",
        backgroundColor: "#ffffff",
        display: "grid",
        gap: "20px",
      }}
    >
      <div>
        <h2 style={{ margin: 0, fontSize: "24px" }}>Сбор живых цитат по нише</h2>
        <p style={{ marginTop: "8px", marginBottom: 0, color: "#4b5563", lineHeight: 1.5 }}>
          Введите нишу и позиционирование эксперта. Система соберёт 10 живых источников и заполнит
          колонки прямыми цитатами людей без додумывания со стороны модели.
        </p>
      </div>

      <form onSubmit={handleSubmit} style={{ display: "grid", gap: "16px" }}>
        <label style={{ display: "grid", gap: "8px" }}>
          <span style={{ fontWeight: 600 }}>Ниша</span>
          <input
            value={niche}
            onChange={(event) => setNiche(event.target.value)}
            placeholder="Например: онлайн-фитнес для женщин 35+, подготовка к IELTS, психолог после развода"
            required
            style={{
              border: "1px solid #d1d5db",
              borderRadius: "10px",
              padding: "12px 14px",
              fontSize: "16px",
            }}
          />
        </label>

        <label style={{ display: "grid", gap: "8px" }}>
          <span style={{ fontWeight: 600 }}>Позиционирование эксперта</span>
          <textarea
            value={positioning}
            onChange={(event) => setPositioning(event.target.value)}
            placeholder="Например: помогаю женщинам после развода вернуть опору, снизить тревогу и мягко выйти в новые отношения без самообмана"
            required
            rows={4}
            style={{
              border: "1px solid #d1d5db",
              borderRadius: "10px",
              padding: "12px 14px",
              fontSize: "16px",
              resize: "vertical",
            }}
          />
        </label>

        <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
          <button
            type="submit"
            disabled={isLoading}
            style={{
              border: "none",
              borderRadius: "10px",
              padding: "12px 18px",
              backgroundColor: isLoading ? "#9ca3af" : "#111827",
              color: "#ffffff",
              cursor: isLoading ? "not-allowed" : "pointer",
              fontSize: "16px",
              fontWeight: 600,
            }}
          >
            {isLoading ? "Собираю живые цитаты..." : "Собрать 10 источников"}
          </button>

          <button
            type="button"
            onClick={handleDownloadCsv}
            disabled={reviews.length === 0}
            style={{
              border: "1px solid #d1d5db",
              borderRadius: "10px",
              padding: "12px 18px",
              backgroundColor: reviews.length === 0 ? "#f3f4f6" : "#ffffff",
              color: "#111827",
              cursor: reviews.length === 0 ? "not-allowed" : "pointer",
              fontSize: "16px",
              fontWeight: 600,
            }}
          >
            Скачать CSV
          </button>
        </div>
      </form>

      {error ? (
        <p
          style={{
            margin: 0,
            color: "#b91c1c",
            backgroundColor: "#fef2f2",
            border: "1px solid #fecaca",
            borderRadius: "10px",
            padding: "12px 14px",
          }}
        >
          {error}
        </p>
      ) : null}

      {lastSearch ? (
        <div
          style={{
            border: "1px solid #e5e7eb",
            borderRadius: "12px",
            padding: "16px",
            backgroundColor: "#f9fafb",
            display: "grid",
            gap: "8px",
          }}
        >
          <p style={{ margin: 0 }}>
            <strong>Ниша:</strong> {lastSearch.niche}
          </p>
          <p style={{ margin: 0 }}>
            <strong>Позиционирование:</strong> {lastSearch.positioning}
          </p>
          <p style={{ margin: 0 }}>
            <strong>Найдено источников:</strong> {reviews.length}
          </p>
        </div>
      ) : null}

      {reviews.length > 0 ? (
        <div style={{ overflowX: "auto" }}>
          <table
            style={{
              width: "100%",
              borderCollapse: "collapse",
              minWidth: "1200px",
            }}
          >
            <thead>
              <tr style={{ backgroundColor: "#f3f4f6" }}>
                {tableHeaders.map((title) => (
                  <th
                    key={title}
                    style={{
                      border: "1px solid #d1d5db",
                      padding: "12px",
                      textAlign: "left",
                      verticalAlign: "top",
                    }}
                  >
                    {title}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {reviews.map((review) => (
                <tr key={review.id}>
                  <td style={cellStyle}>
                    <a href={review.sourceUrl} target="_blank" rel="noreferrer">
                      {review.sourceLabel}
                    </a>
                  </td>
                  <td style={cellStyle}>{review.problem}</td>
                  <td style={cellStyle}>{review.whyNoResult}</td>
                  <td style={cellStyle}>{review.fears}</td>
                  <td style={cellStyle}>{review.desiredResult}</td>
                  <td style={cellStyle}>{review.question}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}
