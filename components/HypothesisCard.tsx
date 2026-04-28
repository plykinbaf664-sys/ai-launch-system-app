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

type ReviewsErrorResponse = {
  error?: string;
};

const tableHeaders = [
  "РСЃС‚РѕС‡РЅРёРє",
  "РџСЂРѕР±Р»РµРјР°",
  "РџРѕС‡РµРјСѓ РґРѕ СЃРёС… РїРѕСЂ РЅРµС‚ СЂРµР·СѓР»СЊС‚Р°С‚Р°",
  "РЎС‚СЂР°С…Рё",
  "Р–РµР»Р°РµРјС‹Р№ СЂРµР·СѓР»СЊС‚Р°С‚",
  "Р’РѕРїСЂРѕСЃ РїСЂРё РїРѕРєСѓРїРєРµ",
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

      const data = (await response.json()) as ReviewsResponse | ReviewsErrorResponse;

      if (!response.ok || !("reviews" in data)) {
        const errorMessage = "error" in data ? data.error : undefined;
        throw new Error(errorMessage || "РќРµ СѓРґР°Р»РѕСЃСЊ СЃРѕР±СЂР°С‚СЊ РѕС‚Р·С‹РІС‹.");
      }

      setReviews(data.reviews);
      setLastSearch({
        niche: data.niche,
        positioning: data.positioning,
      });
    } catch (submitError) {
      const message =
        submitError instanceof Error ? submitError.message : "РџСЂРѕРёР·РѕС€Р»Р° РѕС€РёР±РєР° РїСЂРё СЃР±РѕСЂРµ РѕС‚Р·С‹РІРѕРІ.";
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

    const headers = ["РСЃС‚РѕС‡РЅРёРє", "РЎСЃС‹Р»РєР°", ...tableHeaders.slice(1)];

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
        <h2 style={{ margin: 0, fontSize: "24px" }}>РЎР±РѕСЂ Р¶РёРІС‹С… С†РёС‚Р°С‚ РїРѕ РЅРёС€Рµ</h2>
        <p style={{ marginTop: "8px", marginBottom: 0, color: "#4b5563", lineHeight: 1.5 }}>
          Р’РІРµРґРёС‚Рµ РЅРёС€Сѓ Рё РїРѕР·РёС†РёРѕРЅРёСЂРѕРІР°РЅРёРµ СЌРєСЃРїРµСЂС‚Р°. РЎРёСЃС‚РµРјР° СЃРѕР±РµСЂС‘С‚ 10 Р¶РёРІС‹С… РёСЃС‚РѕС‡РЅРёРєРѕРІ Рё Р·Р°РїРѕР»РЅРёС‚
          РєРѕР»РѕРЅРєРё РїСЂСЏРјС‹РјРё С†РёС‚Р°С‚Р°РјРё Р»СЋРґРµР№ Р±РµР· РґРѕРґСѓРјС‹РІР°РЅРёСЏ СЃРѕ СЃС‚РѕСЂРѕРЅС‹ РјРѕРґРµР»Рё.
        </p>
      </div>

      <form onSubmit={handleSubmit} style={{ display: "grid", gap: "16px" }}>
        <label style={{ display: "grid", gap: "8px" }}>
          <span style={{ fontWeight: 600 }}>РќРёС€Р°</span>
          <input
            value={niche}
            onChange={(event) => setNiche(event.target.value)}
            placeholder="РќР°РїСЂРёРјРµСЂ: РѕРЅР»Р°Р№РЅ-С„РёС‚РЅРµСЃ РґР»СЏ Р¶РµРЅС‰РёРЅ 35+, РїРѕРґРіРѕС‚РѕРІРєР° Рє IELTS, РїСЃРёС…РѕР»РѕРі РїРѕСЃР»Рµ СЂР°Р·РІРѕРґР°"
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
          <span style={{ fontWeight: 600 }}>РџРѕР·РёС†РёРѕРЅРёСЂРѕРІР°РЅРёРµ СЌРєСЃРїРµСЂС‚Р°</span>
          <textarea
            value={positioning}
            onChange={(event) => setPositioning(event.target.value)}
            placeholder="РќР°РїСЂРёРјРµСЂ: РїРѕРјРѕРіР°СЋ Р¶РµРЅС‰РёРЅР°Рј РїРѕСЃР»Рµ СЂР°Р·РІРѕРґР° РІРµСЂРЅСѓС‚СЊ РѕРїРѕСЂСѓ, СЃРЅРёР·РёС‚СЊ С‚СЂРµРІРѕРіСѓ Рё РјСЏРіРєРѕ РІС‹Р№С‚Рё РІ РЅРѕРІС‹Рµ РѕС‚РЅРѕС€РµРЅРёСЏ Р±РµР· СЃР°РјРѕРѕР±РјР°РЅР°"
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
            {isLoading ? "РЎРѕР±РёСЂР°СЋ Р¶РёРІС‹Рµ С†РёС‚Р°С‚С‹..." : "РЎРѕР±СЂР°С‚СЊ 10 РёСЃС‚РѕС‡РЅРёРєРѕРІ"}
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
            РЎРєР°С‡Р°С‚СЊ CSV
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
            <strong>РќРёС€Р°:</strong> {lastSearch.niche}
          </p>
          <p style={{ margin: 0 }}>
            <strong>РџРѕР·РёС†РёРѕРЅРёСЂРѕРІР°РЅРёРµ:</strong> {lastSearch.positioning}
          </p>
          <p style={{ margin: 0 }}>
            <strong>РќР°Р№РґРµРЅРѕ РёСЃС‚РѕС‡РЅРёРєРѕРІ:</strong> {reviews.length}
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
