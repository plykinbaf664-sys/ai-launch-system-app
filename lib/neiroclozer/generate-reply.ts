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

export async function generateNeiroReply(prompt: string) {
  const apiKey = process.env.OPENAI_API_KEY;

  if (!apiKey) {
    throw new Error("Missing OPENAI_API_KEY.");
  }

  const response = await fetch("https://api.openai.com/v1/responses", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model: "gpt-4o-mini",
      input: prompt,
    }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`OpenAI API request failed: ${response.status} ${errorText}`);
  }

  const responseData = (await response.json()) as OpenAIResponse;
  const replyText = extractResponseText(responseData);

  if (!replyText) {
    throw new Error("OpenAI API returned an empty response.");
  }

  return replyText.trim();
}
