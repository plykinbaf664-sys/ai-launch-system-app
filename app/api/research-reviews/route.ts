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

type AnthropicContentItem = {
  type?: string;
  text?: string;
};

type AnthropicResponse = {
  content?: AnthropicContentItem[];
};

type ReviewsPayload = {
  niche: string;
  positioning: string;
  reviews: ReviewRow[];
};

const DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-20250514";
const ANTHROPIC_API_VERSION = "2023-06-01";
const RESEARCH_MAX_TOKENS = 1800;
const REPAIR_MAX_TOKENS = 1200;

const compactSchemaGuide = [
  "{",
  '  "niche": "string",',
  '  "positioning": "string",',
  '  "reviews": [',
  "    {",
  '      "id": "string",',
  '      "sourceLabel": "string",',
  '      "sourceUrl": "string",',
  '      "problem": ">=120 chars direct first-person quote",',
  '      "whyNoResult": ">=120 chars direct first-person quote",',
  '      "fears": ">=120 chars direct first-person quote",',
  '      "desiredResult": ">=120 chars direct first-person quote",',
  '      "question": ">=120 chars direct first-person quote"',
  "    }",
  "  ]",
  "}",
].join("\n");

function extractResponseText(responseData: AnthropicResponse) {
  return (
    responseData.content
      ?.filter((item) => item.type === "text")
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

function isLongString(value: unknown) {
  return typeof value === "string" && value.trim().length >= 120;
}

function isReviewRow(value: unknown): value is ReviewRow {
  if (!value || typeof value !== "object") {
    return false;
  }

  const row = value as ReviewRow;

  return (
    typeof row.id === "string" &&
    typeof row.sourceLabel === "string" &&
    typeof row.sourceUrl === "string" &&
    isLongString(row.problem) &&
    isLongString(row.whyNoResult) &&
    isLongString(row.fears) &&
    isLongString(row.desiredResult) &&
    isLongString(row.question)
  );
}

function isReviewsPayload(value: unknown): value is ReviewsPayload {
  if (!value || typeof value !== "object") {
    return false;
  }

  const payload = value as ReviewsPayload;

  return (
    typeof payload.niche === "string" &&
    typeof payload.positioning === "string" &&
    Array.isArray(payload.reviews) &&
    payload.reviews.length === 10 &&
    payload.reviews.every(isReviewRow)
  );
}

async function callAnthropicApi(payload: object) {
  const apiKey = process.env.ANTHROPIC_API_KEY;

  if (!apiKey) {
    throw new Error("Не найден ANTHROPIC_API_KEY.");
  }

  const response = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-api-key": apiKey,
      "anthropic-version": ANTHROPIC_API_VERSION,
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Anthropic API вернул ошибку: ${errorText}`);
  }

  return (await response.json()) as AnthropicResponse;
}

async function repairMalformedJson(responseText: string, niche: string, positioning: string) {
  const repairedResponse = await callAnthropicApi({
    model: process.env.ANTHROPIC_MODEL || DEFAULT_ANTHROPIC_MODEL,
    max_tokens: REPAIR_MAX_TOKENS,
    system:
      "Convert the text into one valid JSON object. Return only raw JSON with no markdown fences and no commentary.",
    messages: [
      {
        role: "user",
        content: `Target fields:
niche="${niche}"
positioning="${positioning}"

Return one JSON object with 10 reviews.
Required keys in each review: id, sourceLabel, sourceUrl, problem, whyNoResult, fears, desiredResult, question.
Each quote field must stay a direct first-person quote and be at least 120 characters.

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
  "You are a marketing researcher.",
  "Use only open web sources with direct first-person user experience.",
  "Allowed sources: forums, discussions, comments, reviews, Q&A, public posts, complaint threads.",
  "Do not use expert articles, company pages, educational materials, summaries, or paraphrases.",
  "Every quote field must be copied from the source as a direct first-person quote.",
  "If a source lacks a valid quote for a field, skip that source.",
  "Return only raw JSON.",
].join(" ");

function buildUserPrompt(niche: string, positioning: string) {
  return `Ниша: ${niche}
Позиционирование: ${positioning}

Найди до 10 живых источников. Лучше меньше записей, чем слабые или пересказанные цитаты.

Нужны поля:
- sourceLabel
- sourceUrl
- problem
- whyNoResult
- fears
- desiredResult
- question

Правила:
1. Только дословные цитаты от первого лица.
2. Каждая цитата должна подходить только своей колонке.
3. Никаких пересказов и додумывания.
4. Для полей problem, whyNoResult, fears, desiredResult, question длина каждой цитаты минимум 120 символов.

Верни raw JSON без markdown fences по такой форме:
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

    if (!process.env.ANTHROPIC_API_KEY) {
      return Response.json(
        {
          error:
            "Не найден ANTHROPIC_API_KEY. Добавьте ключ в переменные окружения, чтобы включить сбор отзывов.",
        },
        { status: 500 },
      );
    }

    const responseData = await callAnthropicApi({
      model: process.env.ANTHROPIC_MODEL || DEFAULT_ANTHROPIC_MODEL,
      max_tokens: RESEARCH_MAX_TOKENS,
      system: systemPrompt,
      tools: [{ type: "web_search_20250305", name: "web_search", max_uses: 3 }],
      messages: [
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
            "Не удалось прочитать ответ модели. Anthropic вернул ответ без текстового блока в ожидаемом формате.",
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

    if (!isReviewsPayload(parsedJson)) {
      return Response.json(
        {
          error:
            "Ответ модели прочитан, но структура не совпала с ожидаемой. Проверьте, что модель вернула 10 записей и в каждой колонке есть полноценные прямые цитаты людей.",
        },
        { status: 502 },
      );
    }

    return Response.json(parsedJson);
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Неизвестная ошибка при сборе отзывов.";

    return Response.json({ error: message }, { status: 500 });
  }
}
