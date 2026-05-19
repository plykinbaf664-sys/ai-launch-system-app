import asyncio
import csv
import html
import logging
import os
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

import requests
from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from bs4 import BeautifulSoup
from dotenv import load_dotenv


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("telegram_public_web_scraper")


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


@dataclass(frozen=True)
class PublicScraperSettings:
    channels: list[str]
    limit_per_channel: int
    delay_seconds: float
    output_csv: Path
    database_path: Path
    send_to_bot: bool
    tg_lead_bot_token: str
    my_chat_id: str
    dry_run: bool
    request_timeout_seconds: int
    max_post_age_days: int


@dataclass(frozen=True)
class VacancyLead:
    date: datetime | None
    source_channel: str
    recruiter_contact: str
    employer_links: list[str]
    matched_role: str
    snippet: str
    full_text: str
    post_url: str


def parse_bool(value: str) -> bool:
    return value.strip().casefold() in {"1", "true", "yes", "y", "on"}


def load_settings() -> PublicScraperSettings:
    load_dotenv()

    raw_channels = os.getenv("TG_SCRAPER_CHANNELS", "").strip()
    channels = [channel.strip() for channel in raw_channels.split(",") if channel.strip()]
    if not channels:
        raise RuntimeError("Заполни TG_SCRAPER_CHANNELS в .env: нужен хотя бы один публичный Telegram-канал")

    return PublicScraperSettings(
        channels=channels,
        limit_per_channel=int(os.getenv("TG_SCRAPER_LIMIT_PER_CHANNEL", "50")),
        delay_seconds=float(os.getenv("TG_SCRAPER_DELAY_SECONDS", "3")),
        output_csv=Path(os.getenv("TG_SCRAPER_OUTPUT_CSV", "telegram_vacancy_leads.csv")),
        database_path=Path(os.getenv("TG_SCRAPER_DATABASE_PATH", "telegram_vacancy_leads.db")),
        send_to_bot=parse_bool(os.getenv("TG_SCRAPER_SEND_TO_BOT", "true")),
        tg_lead_bot_token=os.getenv("TG_LEAD_BOT", "").strip(),
        my_chat_id=os.getenv("MY_CHAT_ID", "").strip(),
        dry_run=parse_bool(os.getenv("DRY_RUN", "false")),
        request_timeout_seconds=int(os.getenv("TG_SCRAPER_REQUEST_TIMEOUT_SECONDS", "20")),
        max_post_age_days=int(os.getenv("TG_SCRAPER_MAX_POST_AGE_DAYS", "14")),
    )


def normalize_channel_ref(channel_ref: str) -> tuple[str, str]:
    channel_ref = channel_ref.strip()

    if channel_ref.startswith("@"):
        username = channel_ref.removeprefix("@").strip("/")
        return username, f"https://t.me/s/{username}"

    parsed = urlparse(channel_ref)
    if parsed.netloc in {"t.me", "telegram.me"}:
        path = parsed.path.strip("/")
        if path.startswith("+") or path.startswith("joinchat/"):
            raise RuntimeError(f"Приватная invite-ссылка не поддерживается без авторизации: {channel_ref}")
        if path.startswith("s/"):
            username = path.split("/", 1)[1].strip("/")
            return username, f"https://t.me/s/{username}"
        username = path.split("/", 1)[0]
        return username, f"https://t.me/s/{username}"

    username = channel_ref.strip("/")
    return username, f"https://t.me/s/{username}"


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


def clean_text(text: str) -> str:
    return " ".join(text.split())


def truncate_text(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return f"{text[:limit].rstrip()}..."


def make_snippet(text: str, limit: int = 150) -> str:
    return truncate_text(clean_text(text), limit)


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


def extract_recruiter_contact(message_node: BeautifulSoup, text: str) -> str:
    candidates: list[str] = []

    text_node = message_node.select_one(".tgme_widget_message_text")
    if text_node:
        for link in text_node.select("a[href]"):
            href = link.get("href", "")
            if "t.me/" in href or "telegram.me/" in href:
                candidates.append(href)

    candidates.extend(TELEGRAM_LINK_RE.findall(text))
    candidates.extend(USERNAME_RE.findall(text))

    for candidate in candidates:
        contact = normalize_contact(candidate)
        if contact:
            return contact

    return "CONTACT_NOT_FOUND"


def extract_all_links(message_node: BeautifulSoup) -> list[str]:
    links: list[str] = []
    for link in message_node.select("a[href]"):
        href = (link.get("href") or "").strip()
        if not href or href.startswith("#"):
            continue
        if href not in links:
            links.append(href)
    return links


def extract_employer_links(message_node: BeautifulSoup, recruiter_contact: str, post_url: str) -> list[str]:
    employer_links: list[str] = []
    for link in extract_all_links(message_node):
        if link == recruiter_contact or link == post_url:
            continue
        if "t.me/" in link or "telegram.me/" in link:
            continue
        if link not in employer_links:
            employer_links.append(link)
    return employer_links


def parse_message_date(message_node: BeautifulSoup) -> datetime | None:
    time_node = message_node.select_one("time[datetime]")
    if not time_node:
        return None

    raw_datetime = time_node.get("datetime", "")
    try:
        return datetime.fromisoformat(raw_datetime.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        logger.warning("Не удалось распарсить дату сообщения: %s", raw_datetime)
        return None


def parse_message_url(message_node: BeautifulSoup) -> str:
    link_node = message_node.select_one("a.tgme_widget_message_date[href]")
    return link_node.get("href", "") if link_node else ""


class TelegramLeadStorage:
    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        self._init_db()

    def has_processed_post(self, post_url: str) -> bool:
        if not post_url:
            return False

        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM telegram_vacancy_posts WHERE post_url = ? LIMIT 1",
                (post_url,),
            ).fetchone()
        return row is not None

    def mark_processed_post(self, lead: VacancyLead) -> None:
        if not lead.post_url:
            return

        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO telegram_vacancy_posts
                    (post_url, source_channel, recruiter_contact, matched_role, snippet)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    lead.post_url,
                    lead.source_channel,
                    lead.recruiter_contact,
                    lead.matched_role,
                    lead.snippet,
                ),
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._database_path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS telegram_vacancy_posts (
                    post_url TEXT PRIMARY KEY,
                    source_channel TEXT NOT NULL,
                    recruiter_contact TEXT NOT NULL,
                    matched_role TEXT NOT NULL,
                    snippet TEXT NOT NULL,
                    first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )


def fetch_channel_html(url: str, timeout_seconds: int) -> str:
    response = requests.get(
        url,
        timeout=timeout_seconds,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0 Safari/537.36"
            )
        },
    )
    response.raise_for_status()
    return response.text


def scan_channel_sync(
    channel_ref: str,
    settings: PublicScraperSettings,
    storage: TelegramLeadStorage,
) -> list[VacancyLead]:
    username, url = normalize_channel_ref(channel_ref)
    logger.info("Сканирую публичную страницу Telegram: %s", url)

    html_text = fetch_channel_html(url, settings.request_timeout_seconds)
    soup = BeautifulSoup(html_text, "html.parser")
    message_nodes = soup.select(".tgme_widget_message")

    if not message_nodes:
        logger.warning("Сообщения не найдены. Возможно, канал закрыт или недоступен через web-preview: %s", channel_ref)
        return []

    leads: list[VacancyLead] = []
    min_message_date = datetime.utcnow() - timedelta(days=settings.max_post_age_days)
    for message_node in message_nodes[-settings.limit_per_channel :]:
        text_node = message_node.select_one(".tgme_widget_message_text")
        if not text_node:
            continue

        message_date = parse_message_date(message_node)
        if message_date and message_date < min_message_date:
            continue

        text = clean_text(text_node.get_text(" ", strip=True))
        if not text:
            continue

        matched_role = find_matched_role(text)
        if not matched_role:
            continue

        post_url = parse_message_url(message_node)
        if storage.has_processed_post(post_url):
            logger.info("Пропускаю дубль Telegram-поста: %s", post_url)
            continue

        recruiter_contact = extract_recruiter_contact(message_node, text)
        lead = VacancyLead(
            date=message_date,
            source_channel=f"@{username}",
            recruiter_contact=recruiter_contact,
            employer_links=extract_employer_links(message_node, recruiter_contact, post_url),
            matched_role=matched_role,
            snippet=make_snippet(text),
            full_text=text,
            post_url=post_url,
        )
        leads.append(lead)
        storage.mark_processed_post(lead)

    logger.info("Канал обработан: @%s. Найдено новых лидов: %s", username, len(leads))
    return leads


async def collect_vacancy_leads(settings: PublicScraperSettings) -> list[VacancyLead]:
    all_leads: list[VacancyLead] = []
    storage = TelegramLeadStorage(settings.database_path)

    logger.info("Старт публичного Telegram web-scraper")
    logger.info("Каналов в очереди: %s", len(settings.channels))
    logger.info("Активных строгих ролей: %s", ", ".join(ROLE_KEYWORDS))

    for index, channel_ref in enumerate(settings.channels, start=1):
        try:
            logger.info("Канал %s/%s: %s", index, len(settings.channels), channel_ref)
            leads = await asyncio.to_thread(scan_channel_sync, channel_ref, settings, storage)
            all_leads.extend(leads)
        except requests.HTTPError as exc:
            logger.warning("Telegram web-preview вернул HTTP-ошибку для %s: %s", channel_ref, exc)
        except requests.RequestException as exc:
            logger.warning("Не удалось загрузить канал %s: %s", channel_ref, exc)
        except RuntimeError as exc:
            logger.warning("%s", exc)
        except Exception as exc:
            logger.exception("Неожиданная ошибка при обработке канала %s: %s", channel_ref, exc)

        if index < len(settings.channels):
            logger.info("Пауза %.1f сек. перед следующим каналом", settings.delay_seconds)
            await asyncio.sleep(settings.delay_seconds)

    return all_leads


def export_to_csv(leads: list[VacancyLead], output_csv: Path) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    with output_csv.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=(
                "Date",
                "Source_Channel",
                "Recruiter_Contact",
                "Matched_Role",
                "Employer_Links",
                "Snippet",
                "Full_Text",
                "Post_URL",
            ),
        )
        writer.writeheader()
        for lead in leads:
            writer.writerow(
                {
                    "Date": lead.date.strftime("%Y-%m-%d %H:%M") if lead.date else "",
                    "Source_Channel": lead.source_channel,
                    "Recruiter_Contact": lead.recruiter_contact,
                    "Matched_Role": lead.matched_role,
                    "Employer_Links": " | ".join(lead.employer_links),
                    "Snippet": lead.snippet,
                    "Full_Text": lead.full_text,
                    "Post_URL": lead.post_url,
                }
            )

    logger.info("CSV-файл сохранен: %s. Всего новых лидов: %s", output_csv, len(leads))


def build_bot_message(lead: VacancyLead) -> str:
    date = html.escape(lead.date.strftime("%Y-%m-%d %H:%M") if lead.date else "не указана")
    source_channel = html.escape(lead.source_channel)
    recruiter_contact = html.escape(lead.recruiter_contact)
    matched_role = html.escape(lead.matched_role)
    snippet = html.escape(lead.snippet)
    post_url = html.escape(lead.post_url)
    employer_links = html.escape(" | ".join(lead.employer_links) if lead.employer_links else "не найдены")

    post_line = f"\n🔗 <b>Пост:</b> <a href=\"{post_url}\">открыть</a>" if lead.post_url else ""

    return (
        "📌 <b>ТГ ЛИД: вакансия</b>\n\n"
        f"📅 <b>Дата:</b> {date}\n"
        f"📣 <b>Канал:</b> {source_channel}\n"
        f"🎯 <b>Роль:</b> {matched_role}\n"
        f"👤 <b>Контакт:</b> {recruiter_contact}"
        f"{post_line}\n\n"
        f"🏢 <b>Ссылки работодателя:</b>\n{employer_links}\n\n"
        f"💬 <b>Коротко:</b>\n{snippet}"
    )


def build_bot_keyboard(lead: VacancyLead) -> InlineKeyboardMarkup | None:
    buttons: list[list[InlineKeyboardButton]] = []

    if lead.recruiter_contact.startswith(("http://", "https://")):
        buttons.append([InlineKeyboardButton(text="Открыть контакт в Telegram", url=lead.recruiter_contact)])

    if lead.post_url:
        buttons.append([InlineKeyboardButton(text="Открыть пост", url=lead.post_url)])

    return InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None


async def send_leads_to_bot(leads: list[VacancyLead], settings: PublicScraperSettings) -> None:
    if not settings.send_to_bot:
        logger.info("Отправка в Telegram-бот отключена: TG_SCRAPER_SEND_TO_BOT=false")
        return

    if not leads:
        logger.info("Новых лидов для отправки в Telegram-бот нет")
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


async def run_scraper() -> int:
    settings = load_settings()
    all_leads = await collect_vacancy_leads(settings)
    export_to_csv(all_leads, settings.output_csv)
    await send_leads_to_bot(all_leads, settings)
    logger.info("Готово")
    return len(all_leads)


async def run() -> None:
    await run_scraper()


if __name__ == "__main__":
    asyncio.run(run())
