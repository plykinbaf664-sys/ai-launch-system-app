import {
  createLead,
  getActiveExpertProfile,
  getLeadByTelegramUserId,
  insertMessage,
  updateLeadById,
} from "@/lib/supabase-rest";
import {
  parseTelegramPrivateTextMessage,
  sendTextMessage,
  verifyTelegramWebhookSecret,
} from "@/lib/telegram";

function buildGiftText(giftMessage: string, giftUrl: string) {
  return `${giftMessage}\n\n${giftUrl}`;
}

export async function POST(request: Request) {
  try {
    const isSecretValid = await verifyTelegramWebhookSecret(request);

    if (!isSecretValid) {
      return Response.json({ ok: false, error: "Invalid Telegram webhook secret." }, { status: 401 });
    }

    const update = (await request.json()) as { message?: unknown };

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
        status: "active",
        currentStage: "awaiting_first_answer",
      }));

    await updateLeadById(lead.id, {
      expertProfileId: expertProfile.id,
      telegramChatId: incomingMessage.telegramChatId,
      telegramUsername: incomingMessage.telegramUsername,
      firstName: incomingMessage.firstName,
      lastName: incomingMessage.lastName,
      source: "telegram",
      status: "active",
    });

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
    }

    return Response.json({ ok: true });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown webhook error.";
    return Response.json({ ok: false, error: message }, { status: 500 });
  }
}
