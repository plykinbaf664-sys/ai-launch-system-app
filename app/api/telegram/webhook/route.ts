import {
  createLead,
  getActiveExpertFaq,
  getActiveExpertObjections,
  getActiveExpertOffers,
  getActiveExpertProfile,
  getLeadByTelegramUserId,
  getRecentMessagesByLeadId,
  insertMessage,
  updateLeadById,
} from "@/lib/supabase-rest";
import { buildNeiroPrompt } from "@/lib/neiroclozer/prompt-builder";
import { generateNeiroReply } from "@/lib/neiroclozer/generate-reply";
import {
  parseTelegramPrivateTextMessage,
  sendTextMessage,
  verifyTelegramWebhookSecret,
} from "@/lib/telegram";

function buildGiftText(giftMessage: string, giftUrl: string) {
  return `${giftMessage}\n\n${giftUrl}`;
}

function hasAnyKeyword(text: string, keywords: string[]) {
  return keywords.some((keyword) => text.includes(keyword));
}

function detectMatchedOffer(text: string) {
  if (
    hasAnyKeyword(text, [
      "сделайте под ключ",
      "соберите мне",
      "хочу готовую систему",
      "нужно внедрение",
    ])
  ) {
    return "done_for_you";
  }

  if (
    hasAnyKeyword(text, [
      "нужна консультация",
      "нужен совет",
      "хочу понять направление",
    ])
  ) {
    return "consulting";
  }

  if (
    hasAnyKeyword(text, [
      "хочу понять",
      "не понимаю, что делать",
      "нужен разбор",
      "хочу разобраться",
    ])
  ) {
    return "diagnostic";
  }

  return null;
}

function needsManualFollowup(text: string) {
  return hasAnyKeyword(text, [
    "созвон",
    "ручной разбор",
    "обсудить внедрение",
    "готов обсуждать внедрение",
    "как начать работу",
    "начать работу лично",
  ]);
}

function detectWarmthLevel(text: string, matchedOffer: string | null, manualFollowup: boolean) {
  if (
    manualFollowup ||
    hasAnyKeyword(text, [
      "стоимость",
      "цена",
      "сколько стоит",
      "сроки",
      "как начать",
      "подключение",
      "внедрение",
    ])
  ) {
    return "hot";
  }

  if (
    matchedOffer ||
    text.length > 40 ||
    hasAnyKeyword(text, [
      "формат",
      "процесс",
      "как это работает",
      "моя ситуация",
      "у меня",
    ])
  ) {
    return "warm";
  }

  return "cold";
}

function detectLeadStatus(isNewLead: boolean, matchedOffer: string | null, warmthLevel: string, manualFollowup: boolean) {
  if (manualFollowup) {
    return "needs_manual_followup";
  }

  if (matchedOffer && warmthLevel !== "cold") {
    return "qualified";
  }

  if (isNewLead) {
    return "new";
  }

  return "active";
}

export async function POST(request: Request) {
  try {
    const isSecretValid = await verifyTelegramWebhookSecret(request);

    if (!isSecretValid) {
      return Response.json({ ok: false, error: "Invalid Telegram webhook secret." }, { status: 401 });
    }

    const update = (await request.json()) as Parameters<typeof parseTelegramPrivateTextMessage>[0];

    const incomingMessage = parseTelegramPrivateTextMessage(update);

    if (!incomingMessage) {
      return Response.json({ ok: true, ignored: true });
    }

    const expertProfile = await getActiveExpertProfile();

    if (!expertProfile) {
      return Response.json({ ok: false, error: "Active expert_profile not found." }, { status: 500 });
    }

    const existingLead = await getLeadByTelegramUserId(incomingMessage.telegramUserId);
    const isNewLead = !existingLead;
    const normalizedUserText = incomingMessage.text.toLowerCase();
    const matchedOffer = detectMatchedOffer(normalizedUserText) ?? existingLead?.matched_offer ?? null;
    const manualFollowup = needsManualFollowup(normalizedUserText);
    const warmthLevel = detectWarmthLevel(normalizedUserText, matchedOffer, manualFollowup);
    const leadStatus = detectLeadStatus(isNewLead, matchedOffer, warmthLevel, manualFollowup);
    const lead =
      existingLead ??
      (await createLead({
        expertProfileId: expertProfile.id,
        telegramUserId: incomingMessage.telegramUserId,
        telegramChatId: incomingMessage.telegramChatId,
        telegramUsername: incomingMessage.telegramUsername,
        firstName: incomingMessage.firstName,
        lastName: incomingMessage.lastName,
        source: "telegram",
        status: leadStatus,
        currentStage: "awaiting_first_answer",
        matchedOffer,
        lastUserMessage: incomingMessage.text,
        warmthLevel,
      }));

    const updatedLead =
      (await updateLeadById(lead.id, {
        expertProfileId: expertProfile.id,
        telegramChatId: incomingMessage.telegramChatId,
        telegramUsername: incomingMessage.telegramUsername,
        firstName: incomingMessage.firstName,
        lastName: incomingMessage.lastName,
        source: "telegram",
        status: leadStatus,
        matchedOffer,
        lastUserMessage: incomingMessage.text,
        warmthLevel,
      })) ?? lead;

    await insertMessage({
      leadId: lead.id,
      expertProfileId: expertProfile.id,
      direction: "incoming",
      channel: "telegram",
      telegramMessageId: incomingMessage.telegramMessageId,
      text: incomingMessage.text,
      messageType: "user",
    });

    if (isNewLead) {
      const welcomeResult = await sendTextMessage(incomingMessage.telegramChatId, expertProfile.welcome_message);
      await insertMessage({
        leadId: lead.id,
        expertProfileId: expertProfile.id,
        direction: "outgoing",
        channel: "telegram",
        telegramMessageId: welcomeResult.telegramMessageId,
        text: expertProfile.welcome_message,
        messageType: "welcome",
      });

      const giftText = buildGiftText(expertProfile.gift_message, expertProfile.gift_url);
      const giftResult = await sendTextMessage(incomingMessage.telegramChatId, giftText);
      await insertMessage({
        leadId: lead.id,
        expertProfileId: expertProfile.id,
        direction: "outgoing",
        channel: "telegram",
        telegramMessageId: giftResult.telegramMessageId,
        text: giftText,
        messageType: "gift",
      });

      const questionResult = await sendTextMessage(
        incomingMessage.telegramChatId,
        expertProfile.first_qual_question,
      );
      await insertMessage({
        leadId: lead.id,
        expertProfileId: expertProfile.id,
        direction: "outgoing",
        channel: "telegram",
        telegramMessageId: questionResult.telegramMessageId,
        text: expertProfile.first_qual_question,
        messageType: "qual_question",
      });
    } else {
      const [offers, faq, objections, messages] = await Promise.all([
        getActiveExpertOffers(expertProfile.id),
        getActiveExpertFaq(expertProfile.id),
        getActiveExpertObjections(expertProfile.id),
        getRecentMessagesByLeadId(lead.id, 10),
      ]);

      const prompt = buildNeiroPrompt({
        expert: expertProfile,
        offers,
        faq,
        objections,
        lead: updatedLead,
        messages,
      });
      const reply = await generateNeiroReply(prompt);

      await sendTextMessage(incomingMessage.telegramChatId, reply);
    }

    return Response.json({ ok: true });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown webhook error.";
    console.error("Telegram webhook error:", message);
    return Response.json({ ok: false, error: message }, { status: 500 });
  }
}
