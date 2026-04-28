type TelegramUser = {
  id: number;
  username?: string;
  first_name?: string;
  last_name?: string;
};

type TelegramChat = {
  id: number;
  type: string;
};

type TelegramMessage = {
  message_id: number;
  from?: TelegramUser;
  chat: TelegramChat;
  text?: string;
};

type TelegramUpdate = {
  message?: TelegramMessage;
};

export type TelegramPrivateTextMessage = {
  telegramUserId: number;
  telegramChatId: number;
  telegramUsername: string | null;
  firstName: string | null;
  lastName: string | null;
  text: string;
  telegramMessageId: number;
};

type TelegramSendMessageResponse = {
  ok: boolean;
  result?: {
    message_id: number;
    text?: string;
  };
  description?: string;
};

function escapeHtml(value: string) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function convertMarkdownToTelegramHtml(text: string) {
  const codeBlocks: string[] = [];
  const withPlaceholders = text.replace(/```([\s\S]*?)```/g, (_, code: string) => {
    const placeholder = `__CODE_BLOCK_${codeBlocks.length}__`;
    codeBlocks.push(`<pre>${escapeHtml(code.trim())}</pre>`);
    return placeholder;
  });

  let formatted = escapeHtml(withPlaceholders);

  formatted = formatted.replace(
    /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
    (_, label: string, url: string) => `<a href="${escapeHtml(url)}">${label}</a>`,
  );
  formatted = formatted.replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>");
  formatted = formatted.replace(/(^|\W)\*([^*\n]+)\*(?=\W|$)/g, "$1<i>$2</i>");
  formatted = formatted.replace(/`([^`\n]+)`/g, "<code>$1</code>");

  return codeBlocks.reduce(
    (result, block, index) => result.replace(`__CODE_BLOCK_${index}__`, block),
    formatted,
  );
}

function getTelegramBotToken() {
  const token = process.env.TELEGRAM_BOT_TOKEN;

  if (!token) {
    throw new Error("Missing TELEGRAM_BOT_TOKEN.");
  }

  return token;
}

export async function verifyTelegramWebhookSecret(request: Request) {
  const expectedSecret = process.env.TELEGRAM_WEBHOOK_SECRET;

  if (!expectedSecret) {
    return true;
  }

  return request.headers.get("x-telegram-bot-api-secret-token") === expectedSecret;
}

export function parseTelegramPrivateTextMessage(update: TelegramUpdate): TelegramPrivateTextMessage | null {
  const message = update.message;

  if (!message || message.chat.type !== "private" || typeof message.text !== "string") {
    return null;
  }

  const sender = message.from;

  if (!sender) {
    return null;
  }

  const text = message.text.trim();

  if (!text) {
    return null;
  }

  return {
    telegramUserId: sender.id,
    telegramChatId: message.chat.id,
    telegramUsername: sender.username ?? null,
    firstName: sender.first_name ?? null,
    lastName: sender.last_name ?? null,
    text,
    telegramMessageId: message.message_id,
  };
}

export async function sendTextMessage(chatId: number, text: string) {
  const formattedText = convertMarkdownToTelegramHtml(text);

  const response = await fetch(`https://api.telegram.org/bot${getTelegramBotToken()}/sendMessage`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      chat_id: chatId,
      text: formattedText,
      parse_mode: "HTML",
    }),
  });

  const data = (await response.json()) as TelegramSendMessageResponse;

  if (!response.ok || !data.ok || !data.result) {
    throw new Error(data.description || "Telegram sendMessage failed.");
  }

  return {
    telegramMessageId: data.result.message_id,
    text: data.result.text ?? text,
  };
}
