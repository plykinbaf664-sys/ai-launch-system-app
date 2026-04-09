type ReviewRow = {
  id: string;
  sourceLabel: string;
  sourceUrl: string;
  quote: string;
  problem: string;
  excuses: string;
  fears: string;
  desiredResult: string;
  questions: string;
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
          quote: { type: "string" },
          problem: { type: "string" },
          excuses: { type: "string" },
          fears: { type: "string" },
          desiredResult: { type: "string" },
          questions: { type: "string" },
        },
        required: [
          "id",
          "sourceLabel",
          "sourceUrl",
          "quote",
          "problem",
          "excuses",
          "fears",
          "desiredResult",
          "questions",
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

function isReviewsPayload(value: unknown): value is ReviewsPayload {
  if (!value || typeof value !== "object") {
    return false;
  }

  const payload = value as ReviewsPayload;

  return (
    typeof payload.niche === "string" &&
    typeof payload.positioning === "string" &&
    Array.isArray(payload.reviews)
  );
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

    const openAiResponse = await fetch("https://api.openai.com/v1/responses", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${process.env.OPENAI_API_KEY}`,
      },
      body: JSON.stringify({
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
                text:
                  "Ты маркетинговый исследователь. Ищи только открытые веб-источники с реальными формулировками людей. Верни ровно 10 отзывов или сообщений. В поле quote переноси фрагмент в исходной формулировке автора без перефразирования. Не выдумывай данные и не используй источники без прямой цитаты. Для каждого отзыва заполни проблему, оправдания, страхи, желаемый результат и вопросы на основе самой цитаты и контекста страницы. В sourceLabel дай короткое название площадки и материала. В sourceUrl дай прямую ссылку.",
              },
            ],
          },
          {
            role: "user",
            content: [
              {
                type: "input_text",
                text: `Ниша: ${niche}\nПозиционирование эксперта: ${positioning}\n\nНайди 10 релевантных отзывов или публичных сообщений людей, которые соответствуют этой нише и запросу.`,
              },
            ],
          },
        ],
      }),
    });

    if (!openAiResponse.ok) {
      const errorText = await openAiResponse.text();

      return Response.json(
        {
          error: `OpenAI API вернул ошибку: ${errorText}`,
        },
        { status: 502 },
      );
    }

    const responseData = (await openAiResponse.json()) as OpenAIResponse;
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
      return Response.json(
        {
          error: `Модель вернула не JSON. Фрагмент ответа: ${responseText.slice(0, 400)}`,
        },
        { status: 502 },
      );
    }

    if (!isReviewsPayload(parsedJson)) {
      return Response.json(
        {
          error: `Ответ модели прочитан, но структура не совпала с ожидаемой. Фрагмент ответа: ${responseText.slice(0, 400)}`,
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
