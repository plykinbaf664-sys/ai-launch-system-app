type ReviewRow = {
  id: string;
  sourceLabel: string;
  sourceUrl: string;
  clientSituation: string;
  idealResult: string;
  expectations: string;
  whyNoResult: string;
  fears: string;
  pains: string;
  prejudices: string;
  triedBefore: string;
};

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

type ReviewsPayload = {
  niche: string;
  positioning: string;
  reviews: ReviewRow[];
};

const DEFAULT_OPENAI_MODEL = "gpt-4.1";
const RESEARCH_MAX_TOKENS = 3800;
const REPAIR_MAX_TOKENS = 1800;

const compactSchemaGuide = [
  "{",
  '  "niche": "string",',
  '  "positioning": "string",',
  '  "reviews": [',
  "    {",
  '      "id": "string",',
  '      "sourceLabel": "string",',
  '      "sourceUrl": "string",',
  '      "clientSituation": "direct quote or explicit evidence",',
  '      "idealResult": "direct quote or explicit evidence",',
  '      "expectations": "direct quote or explicit evidence",',
  '      "whyNoResult": "direct quote or explicit evidence",',
  '      "fears": "direct quote or explicit evidence",',
  '      "pains": "direct quote or explicit evidence",',
  '      "prejudices": "direct quote or explicit evidence",',
  '      "triedBefore": "direct quote or explicit evidence"',
  "    }",
  "  ]",
  "}",
].join("\n");

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

function asText(value: unknown, fallback = "Не найдено в источнике") {
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}

function normalizeReviewRow(value: unknown, index: number): ReviewRow | null {
  if (!value || typeof value !== "object") {
    return null;
  }

  const row = value as Partial<ReviewRow>;
  const sourceLabel = asText(row.sourceLabel, `Источник ${index + 1}`);
  const sourceUrl = asText(row.sourceUrl, "");

  if (!sourceUrl) {
    return null;
  }

  return {
    id: asText(row.id, `review-${index + 1}`),
    sourceLabel,
    sourceUrl,
    clientSituation: asText(row.clientSituation),
    idealResult: asText(row.idealResult),
    expectations: asText(row.expectations),
    whyNoResult: asText(row.whyNoResult),
    fears: asText(row.fears),
    pains: asText(row.pains),
    prejudices: asText(row.prejudices),
    triedBefore: asText(row.triedBefore),
  };
}

function normalizeReviewsPayload(value: unknown, niche: string, positioning: string): ReviewsPayload | null {
  if (!value || typeof value !== "object") {
    return null;
  }

  const payload = value as ReviewsPayload;
  const reviews = Array.isArray(payload.reviews)
    ? payload.reviews
        .map((review, index) => normalizeReviewRow(review, index))
        .filter((review): review is ReviewRow => Boolean(review))
        .slice(0, 10)
    : [];

  if (reviews.length === 0) {
    return null;
  }

  return {
    niche: asText(payload.niche, niche),
    positioning: asText(payload.positioning, positioning),
    reviews,
  };
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

async function repairMalformedJson(responseText: string, niche: string, positioning: string) {
  const repairedResponse = await callOpenAiApi({
    model: process.env.OPENAI_RESEARCH_MODEL || process.env.OPENAI_MODEL || DEFAULT_OPENAI_MODEL,
    max_output_tokens: REPAIR_MAX_TOKENS,
    instructions:
      "Convert the text into one valid JSON object. Return only raw JSON with no markdown fences and no commentary.",
    input: [
      {
        role: "user",
        content: `Target fields:
niche="${niche}"
positioning="${positioning}"

Return one JSON object with up to 10 reviews.
Required keys in each review: id, sourceLabel, sourceUrl, clientSituation, idealResult, expectations, whyNoResult, fears, pains, prejudices, triedBefore.
Keep direct quotes where possible. Do not invent data.

Malformed text:
${responseText}`,
      },
    ],
  });

  const repairedText = extractResponseText(repairedResponse);

  if (!repairedText) {
    throw new Error("Не удалось восстановить JSON из ответа модели.");
  }

  return JSON.parse(normalizeJsonText(repairedText)) as unknown;
}

const systemPrompt = [
  "You are a concise marketing researcher.",
  "Use web_search and only open first-person sources: reviews, forums, comments, Q&A, public posts.",
  "No expert articles, company pages, summaries, paraphrases, or invented data.",
  "Ground every field in a quote or explicit source evidence.",
  "Return only raw JSON.",
].join(" ");

function buildUserPrompt(niche: string, positioning: string) {
  return `Ниша: ${niche}
Позиционирование: ${positioning}

Через web search найди до 10 живых first-person источников по нише. Лучше меньше релевантных, чем 10 слабых. Заполни:
clientSituation=ситуация клиента; idealResult=идеальный результат; expectations=ожидания; whyNoResult=оправдания отсутствия результата; fears=страхи; pains=боли; prejudices=предрассудки; triedBefore=что уже пробовал.

Правила: только отзывы/форумы/комментарии/Q&A/публичные посты; цитаты или явные факты из источника; без догадок; sourceUrl обязателен; если поля нет в источнике, пиши "Не найдено в источнике"; raw JSON без markdown:
${compactSchemaGuide}`;
}

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as { niche?: string; positioning?: string };
    const niche = body.niche?.trim();
    const positioning = body.positioning?.trim();

    if (!niche || !positioning) {
      return Response.json(
        { error: "Заполните нишу и позиционирование эксперта." },
        { status: 400 },
      );
    }

    if (!process.env.OPENAI_API_KEY) {
      return Response.json(
        {
          error:
            "Не найден OPENAI_API_KEY. Добавьте ключ в переменные окружения, чтобы включить сбор отзывов.",
        },
        { status: 500 },
      );
    }

    const responseData = await callOpenAiApi({
      model: process.env.OPENAI_RESEARCH_MODEL || process.env.OPENAI_MODEL || DEFAULT_OPENAI_MODEL,
      max_output_tokens: RESEARCH_MAX_TOKENS,
      instructions: systemPrompt,
      tools: [{ type: "web_search" }],
      input: [
        {
          role: "user",
          content: buildUserPrompt(niche, positioning),
        },
      ],
    });

    const responseText = extractResponseText(responseData);

    if (!responseText) {
      return Response.json(
        {
          error:
            "Не удалось прочитать ответ модели. OpenAI вернул ответ без текстового блока в ожидаемом формате.",
        },
        { status: 502 },
      );
    }

    let parsedJson: unknown;

    try {
      parsedJson = JSON.parse(normalizeJsonText(responseText));
    } catch {
      parsedJson = await repairMalformedJson(responseText, niche, positioning);
    }

    const normalizedPayload = normalizeReviewsPayload(parsedJson, niche, positioning);

    if (!normalizedPayload) {
      return Response.json(
        {
          error:
            "Ответ модели прочитан, но в нем не найдено ни одной записи с sourceUrl. Попробуйте сузить нишу или уточнить аудиторию.",
        },
        { status: 502 },
      );
    }

    return Response.json(normalizedPayload);
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Неизвестная ошибка при сборе отзывов.";

    return Response.json({ error: message }, { status: 500 });
  }
}
