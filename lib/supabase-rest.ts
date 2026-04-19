type SupabaseLeadRow = {
  id: string;
  expert_profile_id: string | null;
  telegram_user_id: number;
  telegram_chat_id: number;
  telegram_username: string | null;
  first_name: string | null;
  last_name: string | null;
  source: string;
  status: string;
  current_stage: string;
  created_at: string;
  updated_at: string;
};

type SupabaseExpertProfileRow = {
  id: string;
  is_active: boolean;
  expert_name: string;
  welcome_message: string;
  gift_message: string;
  gift_type: "link";
  gift_url: string;
  first_qual_question: string;
  created_at: string;
  updated_at: string;
};

type LeadUpsertInput = {
  expertProfileId: string | null;
  telegramUserId: number;
  telegramChatId: number;
  telegramUsername: string | null;
  firstName: string | null;
  lastName: string | null;
  source: string;
  status: string;
  currentStage: string;
};

type MessageInsertInput = {
  leadId: string;
  expertProfileId: string | null;
  direction: "incoming" | "outgoing";
  channel: "telegram";
  telegramMessageId: number | null;
  text: string;
  messageType: "user" | "welcome" | "gift" | "qual_question";
};

function getSupabaseConfig() {
  const url = process.env.SUPABASE_URL;
  const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

  if (!url || !serviceRoleKey) {
    throw new Error("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY.");
  }

  return { url, serviceRoleKey };
}

async function supabaseRequest<T>(path: string, init?: RequestInit) {
  const { url, serviceRoleKey } = getSupabaseConfig();
  const requestUrl = `${url}/rest/v1/${path}`;
  let response: Response;

  try {
    response = await fetch(requestUrl, {
      ...init,
      headers: {
        apikey: serviceRoleKey,
        Authorization: `Bearer ${serviceRoleKey}`,
        "Content-Type": "application/json",
        ...(init?.headers ?? {}),
      },
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown fetch error.";
    const host = new URL(url).host;
    throw new Error(`Supabase fetch failed for ${host}. Check SUPABASE_URL in .env.local. Original error: ${message}`);
  }

  if (!response.ok) {
    throw new Error(`Supabase request failed: ${response.status} ${await response.text()}`);
  }

  if (response.status === 204) {
    return null as T;
  }

  const responseText = await response.text();

  if (!responseText.trim()) {
    return null as T;
  }

  return JSON.parse(responseText) as T;
}

export async function getActiveExpertProfile() {
  const rows = await supabaseRequest<SupabaseExpertProfileRow[]>(
    "expert_profile?select=*&is_active=eq.true&order=created_at.asc&limit=1",
  );

  return rows[0] ?? null;
}

export async function getLeadByTelegramUserId(telegramUserId: number) {
  const rows = await supabaseRequest<SupabaseLeadRow[]>(
    `leads?select=*&telegram_user_id=eq.${telegramUserId}&limit=1`,
  );

  return rows[0] ?? null;
}

export async function createLead(input: LeadUpsertInput) {
  const rows = await supabaseRequest<SupabaseLeadRow[]>("leads", {
    method: "POST",
    headers: {
      Prefer: "return=representation",
    },
    body: JSON.stringify([
      {
        expert_profile_id: input.expertProfileId,
        telegram_user_id: input.telegramUserId,
        telegram_chat_id: input.telegramChatId,
        telegram_username: input.telegramUsername,
        first_name: input.firstName,
        last_name: input.lastName,
        source: input.source,
        status: input.status,
        current_stage: input.currentStage,
      },
    ]),
  });

  return rows[0];
}

export async function updateLeadById(leadId: string, input: Partial<LeadUpsertInput>) {
  const payload: Record<string, string | number | null> = {};

  if (input.expertProfileId !== undefined) {
    payload.expert_profile_id = input.expertProfileId;
  }
  if (input.telegramChatId !== undefined) {
    payload.telegram_chat_id = input.telegramChatId;
  }
  if (input.telegramUsername !== undefined) {
    payload.telegram_username = input.telegramUsername;
  }
  if (input.firstName !== undefined) {
    payload.first_name = input.firstName;
  }
  if (input.lastName !== undefined) {
    payload.last_name = input.lastName;
  }
  if (input.source !== undefined) {
    payload.source = input.source;
  }
  if (input.status !== undefined) {
    payload.status = input.status;
  }
  if (input.currentStage !== undefined) {
    payload.current_stage = input.currentStage;
  }

  const rows = await supabaseRequest<SupabaseLeadRow[]>(`leads?id=eq.${encodeURIComponent(leadId)}`, {
    method: "PATCH",
    headers: {
      Prefer: "return=representation",
    },
    body: JSON.stringify(payload),
  });

  return rows[0] ?? null;
}

export async function insertMessage(input: MessageInsertInput) {
  await supabaseRequest<null>("messages", {
    method: "POST",
    headers: {
      Prefer: "return=minimal",
    },
    body: JSON.stringify([
      {
        lead_id: input.leadId,
        expert_profile_id: input.expertProfileId,
        direction: input.direction,
        channel: input.channel,
        telegram_message_id: input.telegramMessageId,
        text: input.text,
        message_type: input.messageType,
      },
    ]),
  });
}

export type { SupabaseExpertProfileRow, SupabaseLeadRow };
