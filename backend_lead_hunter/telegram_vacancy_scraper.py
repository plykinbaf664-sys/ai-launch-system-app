import asyncio
import csv
import html
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import (
    ChannelInvalidError,
    ChannelPrivateError,
    FloodWaitError,
    InviteHashExpiredError,
    InviteHashInvalidError,
    UserAlreadyParticipantError,
    UsernameInvalidError,
    UsernameNotOccupiedError,
)
from telethon.tl.functions.messages import CheckChatInviteRequest, ImportChatInviteRequest
from telethon.tl.types import Message, MessageEntityTextUrl, MessageEntityUrl, User


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("telegram_vacancy_scraper")


ROLE_KEYWORDS = (
    "менеджер по продажам",
    "МОП",
    "РОП",
    "Junior Sales Manager",
    "Middle Sales Manager",
    "миддл менеджер по продажам",
    "Сеньор менеджер по партнерским продажам",
    "BizDev",
    "агент продаж",
    "Senior Sales Manager",
    "руководитель отдела продаж",
    "Sales Manager",
)
ROLE_PATTERNS = tuple(
    (keyword, re.compile(rf"(?<![\wА-Яа-яЁё]){re.escape(keyword)}(?![\wА-Яа-яЁё])", re.IGNORECASE))
    for keyword in ROLE_KEYWORDS
)
NON_VACANCY_KEYWORDS = (
    "конференция",
    "вебинар",
    "мастер-класс",
    "мастеркласс",
    "эфир",
    "демо-день",
    "митап",
    "семинар",
    "интенсив",
    "курс",
    "обучение",
    "регистрация",
    "зарегистрируйтесь",
    "участие бесплатно",
    "бесплатная конференция",
    "программа:",
    "в программе",
    "места заканчиваются",
)
NON_TARGET_ROLE_KEYWORDS = (
    "модератор",
    "moderator",
    "brand manager",
    "бренд-менеджер",
    "бренд менеджер",
    "senior brand manager",
    "middle brand manager",
    "junior brand manager",
    "marketing manager",
    "маркетинг менеджер",
    "контент-менеджер",
    "контент менеджер",
    "копирайтер",
    "smm",
    "таргетолог",
    "техническая поддержка",
    "техподдержка",
    "специалист технической поддержки",
    "seo-координатор",
    "seo координатор",
    "seo-специалист",
    "seo специалист",
    "seo/aеo/geo",
    "seo/aeo/geo",
)
HIRING_SIGNALS = (
    "вакансия",
    "ищем",
    "требуется",
    "нужен",
    "нужна",
    "нужны",
    "отклик",
    "откликнуться",
    "резюме",
    "работа",
    "зарплата",
    "оклад",
    "ставка",
    "удаленка",
    "удалёнка",
    "график",
)

TELEGRAM_LINK_RE = re.compile(
    r"(?:https?://)?(?:t\.me|telegram\.me)/[A-Za-z0-9_+/?=&.-]+",
    re.IGNORECASE,
)
USERNAME_RE = re.compile(r"(?<![\w])@[A-Za-z0-9_]{5,32}")
INVITE_RE = re.compile(r"(?:https?://)?t\.me/(?:joinchat/|\+)([A-Za-z0-9_-]+)", re.IGNORECASE)


@dataclass(frozen=True)
class ScraperSettings:
    api_id: int
    api_hash: str
    phone: str
    session_name: str
    channels: list[str]
    limit_per_channel: int
    delay_seconds: float
    output_csv: Path
    send_to_bot: bool
    tg_lead_bot_token: str
    my_chat_id: str
    dry_run: bool


@dataclass(frozen=True)
class VacancyLead:
    date: datetime
    source_channel: str
    recruiter_contact: str
    snippet: str
    full_text: str


def load_settings() -> ScraperSettings:
    load_dotenv()

    api_id = os.getenv("TG_API_ID", "").strip()
    api_hash = os.getenv("TG_API_HASH", "").strip()
    phone = os.getenv("TG_PHONE", "").strip()
    raw_channels = os.getenv("TG_SCRAPER_CHANNELS", "").strip()

    missing = [
        name
        for name, value in (
            ("TG_API_ID", api_id),
            ("TG_API_HASH", api_hash),
            ("TG_PHONE", phone),
            ("TG_SCRAPER_CHANNELS", raw_channels),
        )
        if not value
    ]
    if missing:
        raise RuntimeError(f"Заполни переменные в .env: {', '.join(missing)}")

    channels = [channel.strip() for channel in raw_channels.split(",") if channel.strip()]
    if not channels:
        raise RuntimeError("В TG_SCRAPER_CHANNELS нет ни одного канала для проверки")

    return ScraperSettings(
        api_id=int(api_id),
        api_hash=api_hash,
        phone=phone,
        session_name=os.getenv("TG_SESSION_NAME", "telegram_vacancy_scraper").strip(),
        channels=channels,
        limit_per_channel=int(os.getenv("TG_SCRAPER_LIMIT_PER_CHANNEL", "200")),
        delay_seconds=float(os.getenv("TG_SCRAPER_DELAY_SECONDS", "3")),
        output_csv=Path(os.getenv("TG_SCRAPER_OUTPUT_CSV", "telegram_vacancy_leads.csv")),
        send_to_bot=parse_bool(os.getenv("TG_SCRAPER_SEND_TO_BOT", "true")),
        tg_lead_bot_token=os.getenv("TG_LEAD_BOT", "").strip(),
        my_chat_id=os.getenv("MY_CHAT_ID", "").strip(),
        dry_run=parse_bool(os.getenv("DRY_RUN", "false")),
    )


def parse_bool(value: str) -> bool:
    return value.strip().casefold() in {"1", "true", "yes", "y", "on"}


def find_matched_role(text: str) -> str | None:
    normalized_text = text.casefold()
    if any(keyword in normalized_text for keyword in NON_VACANCY_KEYWORDS):
        return None

    if any(keyword in normalized_text for keyword in NON_TARGET_ROLE_KEYWORDS):
        return None

    if not any(signal in normalized_text for signal in HIRING_SIGNALS):
        return None

    for role, pattern in ROLE_PATTERNS:
        if pattern.search(text):
            return role
    return None


def message_has_keyword(text: str) -> bool:
    return find_matched_role(text) is not None


def clean_text(text: str) -> str:
    return " ".join(text.split())


def make_snippet(text: str, limit: int = 150) -> str:
    text = clean_text(text)
    if len(text) <= limit:
        return text
    return f"{text[:limit].rstrip()}..."


def extract_links_from_entities(message: Message, text: str) -> list[str]:
    links: list[str] = []
    entities = message.entities or []

    for entity in entities:
        if isinstance(entity, MessageEntityTextUrl):
            links.append(entity.url)
            continue

        if isinstance(entity, MessageEntityUrl):
            raw_url = text[entity.offset : entity.offset + entity.length]
            links.append(raw_url)

    return links


async def extract_sender_contact(client: TelegramClient, message: Message) -> str | None:
    sender = await message.get_sender()
    if isinstance(sender, User) and sender.username:
        return f"https://t.me/{sender.username}"
    return None


async def extract_recruiter_contact(client: TelegramClient, message: Message, text: str) -> str:
    entity_links = extract_links_from_entities(message, text)
    regex_links = TELEGRAM_LINK_RE.findall(text)
    usernames = USERNAME_RE.findall(text)

    for value in [*entity_links, *regex_links, *usernames]:
        contact = normalize_contact(value)
        if contact:
            return contact

    sender_contact = await extract_sender_contact(client, message)
    if sender_contact:
        return sender_contact

    return "CONTACT_NOT_FOUND"


def normalize_contact(value: str) -> str | None:
    value = value.strip().rstrip(").,;]")
    if not value:
        return None

    if value.startswith("@"):
        return f"https://t.me/{value.removeprefix('@')}"

    if "t.me/" in value or "telegram.me/" in value:
        if value.startswith("http://") or value.startswith("https://"):
            return value
        return f"https://{value}"

    return None


def get_channel_title(entity: object, fallback: str) -> str:
    title = getattr(entity, "title", None) or getattr(entity, "username", None)
    return str(title) if title else fallback


async def resolve_channel(client: TelegramClient, channel_ref: str) -> object:
    invite_match = INVITE_RE.search(channel_ref)
    if invite_match:
        invite_hash = invite_match.group(1)
        try:
            logger.info("Пробую подключиться по invite-ссылке: %s", channel_ref)
            updates = await client(ImportChatInviteRequest(invite_hash))
            chats = getattr(updates, "chats", None) or []
            if chats:
                return chats[0]
        except UserAlreadyParticipantError:
            logger.info("Аккаунт уже состоит в канале: %s", channel_ref)
            checked_invite = await client(CheckChatInviteRequest(invite_hash))
            chat = getattr(checked_invite, "chat", None)
            if chat:
                return chat
        except (InviteHashExpiredError, InviteHashInvalidError) as exc:
            raise RuntimeError(f"Invite-ссылка недействительна: {channel_ref}") from exc

    return await client.get_entity(channel_ref)


async def scan_channel(
    client: TelegramClient,
    channel_ref: str,
    limit_per_channel: int,
) -> list[VacancyLead]:
    leads: list[VacancyLead] = []

    try:
        entity = await resolve_channel(client, channel_ref)
        channel_title = get_channel_title(entity, channel_ref)
        logger.info("Сканирую канал: %s", channel_title)

        async for message in client.iter_messages(entity, limit=limit_per_channel):
            text = message.message or ""
            if not text or not message_has_keyword(text):
                continue

            contact = await extract_recruiter_contact(client, message, text)
            leads.append(
                VacancyLead(
                    date=message.date.replace(tzinfo=None),
                    source_channel=channel_title,
                    recruiter_contact=contact,
                    snippet=make_snippet(text),
                    full_text=clean_text(text),
                )
            )

        logger.info("Канал обработан: %s. Найдено лидов: %s", channel_title, len(leads))
        return leads

    except FloodWaitError as exc:
        logger.warning("Telegram просит подождать %s секунд. Жду и продолжаю.", exc.seconds)
        await asyncio.sleep(exc.seconds + 5)
        return leads
    except (
        ChannelInvalidError,
        ChannelPrivateError,
        UsernameInvalidError,
        UsernameNotOccupiedError,
        ValueError,
        RuntimeError,
    ) as exc:
        logger.warning("Не удалось прочитать канал %s: %s", channel_ref, exc)
        return leads
    except Exception as exc:
        logger.exception("Неожиданная ошибка при обработке канала %s: %s", channel_ref, exc)
        return leads


def export_to_csv(leads: list[VacancyLead], output_csv: Path) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    with output_csv.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=("Date", "Source_Channel", "Recruiter_Contact", "Snippet", "Full_Text"),
        )
        writer.writeheader()
        for lead in leads:
            writer.writerow(
                {
                    "Date": lead.date.strftime("%Y-%m-%d %H:%M"),
                    "Source_Channel": lead.source_channel,
                    "Recruiter_Contact": lead.recruiter_contact,
                    "Snippet": lead.snippet,
                    "Full_Text": lead.full_text,
                }
            )

    logger.info("CSV-файл сохранен: %s. Всего лидов: %s", output_csv, len(leads))


def build_bot_message(lead: VacancyLead) -> str:
    date = html.escape(lead.date.strftime("%Y-%m-%d %H:%M"))
    source_channel = html.escape(lead.source_channel)
    recruiter_contact = html.escape(lead.recruiter_contact)
    snippet = html.escape(lead.snippet)

    return (
        "📌 <b>ТГ ЛИД: вакансия</b>\n\n"
        f"📅 <b>Дата:</b> {date}\n"
        f"📣 <b>Канал:</b> {source_channel}\n"
        f"👤 <b>Контакт:</b> {recruiter_contact}\n\n"
        f"💬 <b>Коротко:</b>\n{snippet}"
    )


def truncate_text(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return f"{text[:limit].rstrip()}..."


def build_bot_keyboard(lead: VacancyLead) -> InlineKeyboardMarkup | None:
    if not lead.recruiter_contact.startswith(("http://", "https://")):
        return None

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Открыть контакт в Telegram", url=lead.recruiter_contact)]
        ]
    )


async def send_leads_to_bot(leads: list[VacancyLead], settings: ScraperSettings) -> None:
    if not settings.send_to_bot:
        logger.info("Отправка в Telegram-бот отключена: TG_SCRAPER_SEND_TO_BOT=false")
        return

    if not leads:
        logger.info("Лидов для отправки в Telegram-бот нет")
        return

    if not settings.tg_lead_bot_token or not settings.my_chat_id:
        logger.warning("Не заполнены TG_LEAD_BOT или MY_CHAT_ID. CSV сохранен, отправка в бот пропущена.")
        return

    if settings.dry_run:
        logger.info("DRY_RUN=true. Лиды не отправлены в Telegram-бот. Количество: %s", len(leads))
        return

    bot = Bot(token=settings.tg_lead_bot_token)
    try:
        for index, lead in enumerate(leads, start=1):
            await bot.send_message(
                chat_id=settings.my_chat_id,
                text=build_bot_message(lead),
                parse_mode=ParseMode.HTML,
                reply_markup=build_bot_keyboard(lead),
                disable_web_page_preview=True,
            )
            logger.info("Отправлен ТГ-лид %s/%s: %s", index, len(leads), lead.recruiter_contact)
            await asyncio.sleep(0.4)
    finally:
        await bot.session.close()


async def collect_vacancy_leads(settings: ScraperSettings, interactive_auth: bool) -> list[VacancyLead]:
    all_leads: list[VacancyLead] = []

    logger.info("Старт Telegram-скрапера вакансий")
    logger.info("Каналов в очереди: %s", len(settings.channels))

    async with TelegramClient(settings.session_name, settings.api_id, settings.api_hash) as client:
        if interactive_auth:
            await client.start(phone=settings.phone)
        else:
            await client.connect()
            if not await client.is_user_authorized():
                raise RuntimeError(
                    "Telegram-сессия не авторизована. Один раз запусти "
                    "telegram_vacancy_scraper.py из терминала и введи код Telegram."
                )

        for index, channel_ref in enumerate(settings.channels, start=1):
            logger.info("Канал %s/%s: %s", index, len(settings.channels), channel_ref)
            leads = await scan_channel(client, channel_ref, settings.limit_per_channel)
            all_leads.extend(leads)

            if index < len(settings.channels):
                logger.info("Пауза %.1f сек. перед следующим каналом", settings.delay_seconds)
                await asyncio.sleep(settings.delay_seconds)

    return all_leads


async def run_scraper(interactive_auth: bool = False) -> int:
    settings = load_settings()
    all_leads = await collect_vacancy_leads(settings, interactive_auth=interactive_auth)
    export_to_csv(all_leads, settings.output_csv)
    await send_leads_to_bot(all_leads, settings)
    logger.info("Готово")
    return len(all_leads)


async def run() -> None:
    await run_scraper(interactive_auth=True)


if __name__ == "__main__":
    asyncio.run(run())
