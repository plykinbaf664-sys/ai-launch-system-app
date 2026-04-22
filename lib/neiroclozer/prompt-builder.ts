import type {
  SupabaseExpertFaqRow,
  SupabaseExpertObjectionRow,
  SupabaseExpertOfferRow,
  SupabaseExpertProfileRow,
  SupabaseLeadRow,
  SupabaseMessageRow,
} from "@/lib/supabase-rest";

type BuildNeiroPromptParams = {
  expert: SupabaseExpertProfileRow;
  offers: SupabaseExpertOfferRow[];
  faq: SupabaseExpertFaqRow[];
  objections: SupabaseExpertObjectionRow[];
  lead: SupabaseLeadRow;
  messages: SupabaseMessageRow[];
};

function valueOrFallback(value: string | null | undefined, fallback = "Не указано") {
  return value?.trim() || fallback;
}

function formatOffers(offers: SupabaseExpertOfferRow[]) {
  if (offers.length === 0) {
    return "Офферы не указаны.";
  }

  return offers
    .map((offer, index) => {
      return [
        `${index + 1}. ${offer.title}`,
        `Описание: ${valueOrFallback(offer.description)}`,
        `Цена: ${valueOrFallback(offer.price_text)}`,
        `CTA: ${valueOrFallback(offer.cta_text)}`,
      ].join("\n");
    })
    .join("\n\n");
}

function formatFaq(faq: SupabaseExpertFaqRow[]) {
  if (faq.length === 0) {
    return "FAQ не указан.";
  }

  return faq
    .map((item, index) => {
      return [`${index + 1}. Вопрос: ${item.question}`, `Ответ: ${item.answer}`].join("\n");
    })
    .join("\n\n");
}

function formatObjections(objections: SupabaseExpertObjectionRow[]) {
  if (objections.length === 0) {
    return "Возражения не указаны.";
  }

  return objections
    .map((item, index) => {
      return [`${index + 1}. Возражение: ${item.objection}`, `Ответ: ${item.response}`].join("\n");
    })
    .join("\n\n");
}

function formatMessages(messages: SupabaseMessageRow[]) {
  if (messages.length === 0) {
    return "История диалога пока пустая.";
  }

  return [...messages]
    .sort((a, b) => a.created_at.localeCompare(b.created_at))
    .map((message) => {
      const author = message.direction === "incoming" ? "Пользователь" : "Эксперт";
      return `${author}: ${message.text}`;
    })
    .join("\n");
}

export function buildNeiroPrompt(params: BuildNeiroPromptParams) {
  const { expert, offers, faq, objections, lead, messages } = params;

  return [
    "Ты отвечаешь в Telegram от лица эксперта.",
    "",
    "## Эксперт",
    `Имя эксперта: ${expert.expert_name}`,
    `Бренд: ${valueOrFallback(expert.brand_name)}`,
    `Роль: ${valueOrFallback(expert.role_description)}`,
    `Позиционирование: ${valueOrFallback(expert.core_positioning)}`,
    `Целевая аудитория: ${valueOrFallback(expert.target_audience)}`,
    "",
    "## Тон и правила коммуникации",
    valueOrFallback(expert.communication_rules),
    "",
    "## Что нельзя говорить",
    valueOrFallback(expert.do_not_say_rules),
    "",
    "## Офферы",
    formatOffers(offers),
    "",
    "## FAQ",
    formatFaq(faq),
    "",
    "## Возражения и ответы",
    formatObjections(objections),
    "",
    "## Лид",
    `Status: ${lead.status}`,
    `Warmth level: ${lead.warmth_level}`,
    `Matched offer: ${valueOrFallback(lead.matched_offer, "Пока не определен")}`,
    `Last user message: ${valueOrFallback(lead.last_user_message, "Пока нет")}`,
    "",
    "## Последние сообщения диалога",
    formatMessages(messages),
    "",
    "## Инструкции для ответа",
    "Отвечай как живой человек.",
    "Не пиши как бот.",
    "Не используй длинные объяснения.",
    "Пиши коротко, понятно и по ситуации.",
    "Учитывай статус лида, теплоту и последнее сообщение.",
    "Веди к следующему шагу: диагностике, продаже, разбору или созвону, если это уместно.",
    "Не выдумывай факты, которых нет в данных выше.",
  ].join("\n");
}

export type { BuildNeiroPromptParams };
