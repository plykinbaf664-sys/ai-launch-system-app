import type { CompetitorLevel, CompetitorRow, ReviewRow } from "@/components/research/types";

type OpenAIContentItem = {
  type?: string;
  text?: string;
};

type OpenAIOutputItem = {
  type?: string;
  content?: OpenAIContentItem[];
};

type OpenAIResponse = {
  output_text?: string;
  output?: OpenAIOutputItem[];
};

type CompetitorsPayload = {
  competitors: CompetitorRow[];
};

const DEFAULT_OPENAI_MODEL = "gpt-4.1";
const COMPETITOR_MAX_TOKENS = 4200;
const levels: CompetitorLevel[] = ["Крупный", "Средний", "Нишевый", "Дополнительный"];
const targetLevelOrder: CompetitorLevel[] = [
  "Крупный",
  "Крупный",
  "Крупный",
  "Средний",
  "Средний",
  "Средний",
  "Нишевый",
  "Нишевый",
  "Нишевый",
  "Дополнительный",
];

function extractResponseText(responseData: OpenAIResponse) {
  if (responseData.output_text?.trim()) {
    return responseData.output_text.trim();
  }

  return (
    responseData.output
      ?.flatMap((item) => item.content || [])
      .filter((item) => item.type === "output_text" || item.type === "text")
      .map((item) => item.text?.trim())
      .filter((item): item is string => Boolean(item))
      .join("\n")
      .trim() || ""
  );
}

function normalizeJsonText(value: string) {
  const trimmed = value.trim();

  if (!trimmed.startsWith("```")) {
    return trimmed;
  }

  return trimmed
    .replace(/^```[a-zA-Z0-9_-]*\s*/, "")
    .replace(/\s*```$/, "")
    .trim();
}

function asText(value: unknown, fallback = "Не найдено в открытых источниках") {
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}

function normalizeLevel(value: unknown): CompetitorLevel | null {
  const text = typeof value === "string" ? value.trim().toLowerCase() : "";

  if (text.includes("круп")) {
    return "Крупный";
  }

  if (text.includes("сред")) {
    return "Средний";
  }

  if (text.includes("ниш")) {
    return "Нишевый";
  }

  if (text.includes("доп")) {
    return "Дополнительный";
  }

  return levels.includes(value as CompetitorLevel) ? (value as CompetitorLevel) : null;
}

function nextAvailableLevel(counts: Record<CompetitorLevel, number>) {
  return targetLevelOrder.find((level) => counts[level] < targetLevelOrder.filter((item) => item === level).length);
}

function normalizeCompetitorRow(
  value: unknown,
  index: number,
  counts: Record<CompetitorLevel, number>,
): CompetitorRow | null {
  if (!value || typeof value !== "object") {
    return null;
  }

  const row = value as Partial<CompetitorRow>;
  const name = asText(row.name, "");

  if (!name) {
    return null;
  }

  const normalizedLevel = normalizeLevel(row.level);
  const level = normalizedLevel && counts[normalizedLevel] < targetLevelOrder.filter((item) => item === normalizedLevel).length
    ? normalizedLevel
    : nextAvailableLevel(counts);

  if (!level) {
    return null;
  }

  counts[level] += 1;

  return {
    id: asText(row.id, `competitor-${index + 1}`),
    name,
    platform: asText(row.platform),
    level,
    positioning: asText(row.positioning),
    audienceSegment: asText(row.audienceSegment),
    mainPromise: asText(row.mainPromise),
    differentiator: asText(row.differentiator),
    products: asText(row.products),
    prices: asText(row.prices, "Не указано"),
    leadMagnets: asText(row.leadMagnets),
    funnel: asText(row.funnel),
    instagramContent: asText(row.instagramContent),
  };
}

function normalizeCompetitorsPayload(value: unknown): CompetitorsPayload | null {
  if (!value || typeof value !== "object") {
    return null;
  }

  const payload = value as CompetitorsPayload;
  const counts: Record<CompetitorLevel, number> = { Крупный: 0, Средний: 0, Нишевый: 0, Дополнительный: 0 };
  const competitors = Array.isArray(payload.competitors)
    ? payload.competitors
        .map((competitor, index) => normalizeCompetitorRow(competitor, index, counts))
        .filter((competitor): competitor is CompetitorRow => Boolean(competitor))
        .slice(0, 10)
    : [];

  if (competitors.length !== 10) {
    return null;
  }

  return { competitors };
}

async function callOpenAiApi(payload: object) {
  const apiKey = process.env.OPENAI_API_KEY;

  if (!apiKey) {
    throw new Error("Не найден OPENAI_API_KEY.");
  }

  const response = await fetch("https://api.openai.com/v1/responses", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`OpenAI API вернул ошибку: ${errorText}`);
  }

  return (await response.json()) as OpenAIResponse;
}

function buildReviewSignals(reviews: ReviewRow[]) {
  return reviews
    .slice(0, 5)
    .map((review, index) => ({
      n: index + 1,
      pain: review.pains.slice(0, 180),
      result: review.idealResult.slice(0, 180),
      fear: review.fears.slice(0, 160),
      tried: review.triedBefore.slice(0, 160),
    }));
}

function buildPrompt(niche: string, positioning: string, reviews: ReviewRow[]) {
  return `Ниша: ${niche}
Позиционирование: ${positioning}
Сигналы из отзывов: ${JSON.stringify(buildReviewSignals(reviews))}

Найди через веб-поиск 10 реальных конкурентов: 3 крупных, 3 средних, 3 нишевых, 1 дополнительный. Не выдумывай бренды. Если точных цен нет, пиши "не указано".

Верни только JSON с 10 объектами в массиве competitors. Порядок уровней строго такой: 1-3 "Крупный", 4-6 "Средний", 7-9 "Нишевый", 10 "Дополнительный".
{"competitors":[{"id":"c1","name":"","platform":"","level":"Крупный","positioning":"","audienceSegment":"","mainPromise":"","differentiator":"","products":"","prices":"","leadMagnets":"","funnel":"","instagramContent":""}]}

Правила: все поля строковые; не оставляй пустые строки; если данных нет, пиши "не указано"; поля кратко, по делу, на русском; instagramContent = что, судя по открытым данным, набирает больше просмотров.`;
}

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as {
      niche?: string;
      positioning?: string;
      reviews?: ReviewRow[];
    };
    const niche = body.niche?.trim();
    const positioning = body.positioning?.trim();
    const reviews = Array.isArray(body.reviews) ? body.reviews : [];

    if (!niche || !positioning || reviews.length === 0) {
      return Response.json(
        { error: "Нужны ниша, позиционирование и отзывы для анализа конкурентов." },
        { status: 400 },
      );
    }

    if (!process.env.OPENAI_API_KEY) {
      return Response.json(
        {
          error:
            "Не найден OPENAI_API_KEY. Добавьте ключ в переменные окружения, чтобы включить анализ конкурентов.",
        },
        { status: 500 },
      );
    }

    const responseData = await callOpenAiApi({
      model: process.env.OPENAI_RESEARCH_MODEL || process.env.OPENAI_MODEL || DEFAULT_OPENAI_MODEL,
      max_output_tokens: COMPETITOR_MAX_TOKENS,
      instructions:
        "You are a concise market researcher. Use web_search. Return only valid raw JSON. No markdown.",
      tools: [{ type: "web_search" }],
      input: [{ role: "user", content: buildPrompt(niche, positioning, reviews) }],
    });

    const responseText = extractResponseText(responseData);

    if (!responseText) {
      return Response.json(
        { error: "Не удалось прочитать ответ модели по конкурентам." },
        { status: 502 },
      );
    }

    const parsedJson = JSON.parse(normalizeJsonText(responseText)) as unknown;

    const normalizedPayload = normalizeCompetitorsPayload(parsedJson);

    if (!normalizedPayload) {
      return Response.json(
        {
          error:
            "Ответ по конкурентам прочитан, но в нем не найдено 10 конкурентов. Попробуйте уточнить нишу или аудиторию.",
        },
        { status: 502 },
      );
    }

    return Response.json(normalizedPayload);
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Неизвестная ошибка при сборе конкурентов.";

    return Response.json({ error: message }, { status: 500 });
  }
}
