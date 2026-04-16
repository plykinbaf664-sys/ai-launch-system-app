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

type OpenAIContentItem = {
  type?: string;
  text?: string;
};

type OpenAIOutputItem = {
  type?: string;
  content?: OpenAIContentItem[];
};

type OpenAIResponse = {
  output?: OpenAIOutputItem[];
  output_text?: string;
};

type ReviewsPayload = {
  niche: string;
  positioning: string;
  reviews: ReviewRow[];
};

const paragraphQuoteSchema = {
  type: "string",
  minLength: 120,
} as const;

const outputSchema = {
  type: "object",
  additionalProperties: false,
  properties: {
    niche: { type: "string" },
    positioning: { type: "string" },
    reviews: {
      type: "array",
      minItems: 10,
      maxItems: 10,
      items: {
        type: "object",
        additionalProperties: false,
        properties: {
          id: { type: "string" },
          sourceLabel: { type: "string" },
          sourceUrl: { type: "string" },
          problem: paragraphQuoteSchema,
          whyNoResult: paragraphQuoteSchema,
          fears: paragraphQuoteSchema,
          desiredResult: paragraphQuoteSchema,
          question: paragraphQuoteSchema,
        },
        required: [
          "id",
          "sourceLabel",
          "sourceUrl",
          "problem",
          "whyNoResult",
          "fears",
          "desiredResult",
          "question",
        ],
      },
    },
  },
  required: ["niche", "positioning", "reviews"],
} as const;

function extractResponseText(responseData: OpenAIResponse) {
  if (typeof responseData.output_text === "string" && responseData.output_text.trim()) {
    return responseData.output_text.trim();
  }

  const contentText = responseData.output
    ?.flatMap((item) => item.content ?? [])
    .map((item) => item.text?.trim())
    .filter((item): item is string => Boolean(item))
    .join("\n")
    .trim();

  return contentText || "";
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

async function callResponsesApi(payload: object) {
  const response = await fetch("https://api.openai.com/v1/responses", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${process.env.OPENAI_API_KEY}`,
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`OpenAI API вернул ошибку: ${errorText}`);
  }

  return (await response.json()) as OpenAIResponse;
}

async function repairMalformedJson(responseText: string) {
  const repairedResponse = await callResponsesApi({
    model: "gpt-4.1",
    text: {
      format: {
        type: "json_schema",
        name: "review_research_repair",
        schema: outputSchema,
        strict: true,
      },
    },
    input: [
      {
        role: "system",
        content: [
          {
            type: "input_text",
            text:
              "You repair malformed JSON. Convert the provided text into valid JSON that matches the schema exactly. Do not add commentary. Preserve the content as-is whenever possible.",
          },
        ],
      },
      {
        role: "user",
        content: [
          {
            type: "input_text",
            text: responseText,
          },
        ],
      },
    ],
  });

  const repairedText = extractResponseText(repairedResponse);

  if (!repairedText) {
    throw new Error("Не удалось восстановить JSON из ответа модели.");
  }

  return JSON.parse(repairedText) as unknown;
}

const systemPrompt =
  "You are a marketing researcher. Search only open web sources with direct first-person user experience: forums, discussions, comments, reviews, Q&A threads, public posts, and complaint threads. Use only direct quotes from potential customers. Never use expert articles, educational materials, editorial summaries, journalist retellings, third-person case studies, company/app copy, landing pages, feature descriptions, or any informational site text. Never paraphrase, infer, summarize, normalize, or correct wording. Every non-source field must be a substantial first-person quote copied from the source as a full paragraph. Prefer fewer records over doubtful ones. Strict relevance test for every non-source cell: the quote must directly answer that exact column question, must fit only that column, and must not rely on guessed meaning. If a source has no direct quote for a column, leave the column empty or skip the source. Column rules: problem = current pain or unsatisfactory situation; whyNoResult = explicit reason progress is blocked or inconsistent; fears = explicit fear, worry, or risk; desiredResult = explicit wanted outcome or state; question = explicit buying-related question or hesitation before choosing, purchasing, or starting. Return only valid JSON.";

function buildUserPrompt(niche: string, positioning: string) {
  return `Ниша: ${niche}
Позиционирование эксперта: ${positioning}

Найди релевантные живые источники и верни до 10 записей. Лучше вернуть меньше записей, чем подставить пересказ, экспертную статью или неавтентичную цитату.

Колонки: sourceLabel, problem, whyNoResult, fears, desiredResult, question.

Строгая проверка релевантности для каждой ячейки:
1. Цитата прямо отвечает на вопрос этой колонки.
2. Это дословные слова самого человека от первого лица.
3. Смысл относится только к этой колонке, а не к соседней.
4. Нет пересказа, догадки, расширения смысла или подстановки соседнего текста.
5. Если хотя бы один пункт не выполняется, ячейка должна остаться пустой или источник должен быть пропущен.

Семантика колонок:
- problem: только текущая боль или неудовлетворяющая ситуация.
- whyNoResult: только причина, почему до сих пор нет результата.
- fears: только явный страх, тревога или риск.
- desiredResult: только явный желаемый итог или состояние.
- question: только вопрос или сомнение перед покупкой, выбором или стартом решения.`;
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

    const responseData = await callResponsesApi({
      model: "gpt-4.1",
      tools: [{ type: "web_search_preview" }],
      tool_choice: "auto",
      text: {
        format: {
          type: "json_schema",
          name: "review_research",
          schema: outputSchema,
          strict: true,
        },
      },
      input: [
        {
          role: "system",
          content: [
            {
              type: "input_text",
              text: systemPrompt,
            },
          ],
        },
        {
          role: "user",
          content: [
            {
              type: "input_text",
              text: buildUserPrompt(niche, positioning),
            },
          ],
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
      parsedJson = JSON.parse(responseText);
    } catch {
      parsedJson = await repairMalformedJson(responseText);
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
