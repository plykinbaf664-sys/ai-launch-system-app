import asyncio
import csv
import html
import logging
import os
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import requests
from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramRetryAfter
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from bs4 import BeautifulSoup
from dotenv import load_dotenv


logger = logging.getLogger("hh_html_scraper")

HH_BASE_URL = "https://hh.ru"
ROLE_KEYWORDS = (
    "РОП",
    "руководитель отдела продаж",
    "менеджер по продажам",
    "Junior Sales Manager",
    "Middle Sales Manager",
    "Senior Sales Manager",
    "Sales Manager",
)
ROLE_PATTERNS = tuple(
    (role, re.compile(rf"(?<![\wА-Яа-яЁё]){re.escape(role)}(?![\wА-Яа-яЁё])", re.IGNORECASE))
    for role in ROLE_KEYWORDS
)
STOP_ROLE_KEYWORDS = (
    "модератор",
    "brand manager",
    "бренд-менеджер",
    "маркетолог",
    "smm",
    "таргетолог",
    "копирайтер",
    "техподдержка",
    "техническая поддержка",
    "seo",
    "контент",
    "hr",
    "рекрутер",
    "оператор",
    "администратор",
)
B2B_KEYWORDS = (
    "b2b",
    "корпоратив",
    "корпоративные клиенты",
    "юридические лица",
    "saas",
    "it",
    "интегратор",
    "партнерские продажи",
    "партнёрские продажи",
    "дилер",
    "дистрибьютор",
)
B2C_KEYWORDS = (
    "b2c",
    "розница",
    "физические лица",
    "колл-центр",
    "call-центр",
    "недвижимость",
    "страхование",
    "банк",
    "интернет-магазин",
    "онлайн-школа",
)


@dataclass(frozen=True)
class HHScraperSettings:
    queries: list[str]
    area: str
    max_age_days: int
    max_pages: int
    per_page: int
    delay_seconds: float
    output_csv: Path
    database_path: Path
    send_to_bot: bool
    tg_lead_bot_token: str
    my_chat_id: str
    dry_run: bool
    request_timeout_seconds: int
    bot_send_delay_seconds: float
    max_leads_per_run: int
    max_bot_messages_per_run: int


@dataclass(frozen=True)
class HHVacancyLead:
    vacancy_id: str
    title: str
    matched_role: str
    segment: str
    company: str
    salary: str
    location: str
    published_at: str
    url: str
    snippet: str


def parse_bool(value: str) -> bool:
    return value.strip().casefold() in {"1", "true", "yes", "y", "on"}


def split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def load_settings() -> HHScraperSettings:
    load_dotenv()

    return HHScraperSettings(
        queries=split_csv(os.getenv("HH_SCRAPER_QUERIES", ",".join(ROLE_KEYWORDS))),
        area=os.getenv("HH_SCRAPER_AREA", "113").strip(),
        max_age_days=int(os.getenv("HH_SCRAPER_MAX_POST_AGE_DAYS", "14")),
        max_pages=int(os.getenv("HH_SCRAPER_MAX_PAGES", "3")),
        per_page=int(os.getenv("HH_SCRAPER_PER_PAGE", "20")),
        delay_seconds=float(os.getenv("HH_SCRAPER_DELAY_SECONDS", "2")),
        output_csv=Path(os.getenv("HH_SCRAPER_OUTPUT_CSV", "hh_vacancy_leads.csv")),
        database_path=Path(os.getenv("HH_SCRAPER_DATABASE_PATH", "hh_vacancy_leads.db")),
        send_to_bot=parse_bool(os.getenv("HH_SCRAPER_SEND_TO_BOT", "true")),
        tg_lead_bot_token=os.getenv("TG_LEAD_BOT", "").strip(),
        my_chat_id=os.getenv("MY_CHAT_ID", "").strip(),
        dry_run=parse_bool(os.getenv("DRY_RUN", "false")),
        request_timeout_seconds=int(os.getenv("HH_SCRAPER_REQUEST_TIMEOUT_SECONDS", "20")),
        bot_send_delay_seconds=float(os.getenv("HH_SCRAPER_BOT_SEND_DELAY_SECONDS", "2")),
        max_leads_per_run=int(os.getenv("HH_SCRAPER_MAX_LEADS_PER_RUN", "20")),
        max_bot_messages_per_run=int(os.getenv("HH_SCRAPER_MAX_BOT_MESSAGES_PER_RUN", "20")),
    )


def clean_text(text: str) -> str:
    return " ".join(text.split())


def absolute_hh_url(url: str) -> str:
    if not url:
        return ""
    if url.startswith("http"):
        return url
    if url.startswith("/"):
        return f"{HH_BASE_URL}{url}"
    return url


def extract_vacancy_id(url: str) -> str:
    path = urlparse(url).path
    match = re.search(r"/vacancy/(\d+)", path)
    if match:
        return match.group(1)
    return url


def find_matched_role(text: str) -> str | None:
    normalized_text = text.casefold()
    if any(keyword in normalized_text for keyword in STOP_ROLE_KEYWORDS):
        return None

    for role, pattern in ROLE_PATTERNS:
        if pattern.search(text):
            return role
    return None


def detect_segment(text: str) -> str:
    normalized_text = text.casefold()
    if any(keyword in normalized_text for keyword in B2B_KEYWORDS):
        return "B2B"
    if any(keyword in normalized_text for keyword in B2C_KEYWORDS):
        return "B2C"
    return "Unknown"


class HHLeadStorage:
    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        self._init_db()

    def has_seen(self, vacancy_id: str) -> bool:
        with self._connect() as conn:
            row = conn.execute("SELECT 1 FROM hh_vacancy_posts WHERE vacancy_id = ? LIMIT 1", (vacancy_id,)).fetchone()
        return row is not None

    def mark_seen(self, lead: HHVacancyLead) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO hh_vacancy_posts
                    (vacancy_id, title, company, url, matched_role, segment)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (lead.vacancy_id, lead.title, lead.company, lead.url, lead.matched_role, lead.segment),
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._database_path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS hh_vacancy_posts (
                    vacancy_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    company TEXT NOT NULL,
                    url TEXT NOT NULL,
                    matched_role TEXT NOT NULL,
                    segment TEXT NOT NULL,
                    first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )


def build_search_url(query: str, settings: HHScraperSettings, page: int) -> str:
    params = {
        "text": query,
        "area": settings.area,
        "search_field": "name",
        "search_period": str(settings.max_age_days),
        "order_by": "publication_time",
        "items_on_page": str(settings.per_page),
        "page": str(page),
    }
    return f"{HH_BASE_URL}/search/vacancy?{urlencode(params)}"


def fetch_html(session: requests.Session, url: str, timeout_seconds: int) -> str:
    response = session.get(url, timeout=timeout_seconds)
    response.raise_for_status()
    return response.text


def first_text(node: BeautifulSoup, selectors: tuple[str, ...]) -> str:
    for selector in selectors:
        found = node.select_one(selector)
        if found:
            value = clean_text(found.get_text(" ", strip=True))
            if value:
                return value
    return ""


def find_vacancy_cards(soup: BeautifulSoup) -> list[BeautifulSoup]:
    cards = soup.select('[data-qa="vacancy-serp__vacancy"]')
    if cards:
        return cards

    title_links = soup.select('a[href*="/vacancy/"]')
    cards = []
    for link in title_links:
        card = link.find_parent(attrs={"data-qa": re.compile("vacancy")}) or link.find_parent("div")
        if card and card not in cards:
            cards.append(card)
    return cards


def parse_card(card: BeautifulSoup) -> HHVacancyLead | None:
    title_link = (
        card.select_one('[data-qa="serp-item__title"]')
        or card.select_one('[data-qa="vacancy-serp__vacancy-title"]')
        or card.select_one('a[href*="/vacancy/"]')
    )
    if not title_link:
        return None

    title = clean_text(title_link.get_text(" ", strip=True))
    url = absolute_hh_url(title_link.get("href", ""))
    if not title or not url:
        return None

    text_for_filter = clean_text(card.get_text(" ", strip=True))
    matched_role = find_matched_role(f"{title} {text_for_filter}")
    if not matched_role:
        return None

    company = first_text(
        card,
        (
            '[data-qa="vacancy-serp__vacancy-employer"]',
            '[data-qa="vacancy-serp__vacancy-employer-text"]',
            '[data-qa="vacancy-serp__vacancy-employer"] a',
        ),
    )
    salary = first_text(
        card,
        (
            '[data-qa="vacancy-serp__vacancy-compensation"]',
            '[data-qa="vacancy-serp__vacancy-salary"]',
        ),
    )
    location = first_text(card, ('[data-qa="vacancy-serp__vacancy-address"]', '[data-qa="vacancy-serp__vacancy-work-address"]'))
    published_at = first_text(card, ('[data-qa="vacancy-serp__vacancy-date"]', "time"))

    return HHVacancyLead(
        vacancy_id=extract_vacancy_id(url),
        title=title,
        matched_role=matched_role,
        segment=detect_segment(text_for_filter),
        company=company or "не указано",
        salary=salary or "не указано",
        location=location or "не указано",
        published_at=published_at,
        url=url,
        snippet=clean_text(text_for_filter)[:220],
    )


def scan_hh_sync(settings: HHScraperSettings) -> list[HHVacancyLead]:
    storage = HHLeadStorage(settings.database_path)
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
            ),
            "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
        }
    )

    leads: list[HHVacancyLead] = []
    for query in settings.queries:
        for page in range(settings.max_pages):
            if len(leads) >= settings.max_leads_per_run:
                logger.info("Достигнут лимит HH-лидов за запуск: %s", settings.max_leads_per_run)
                return leads

            url = build_search_url(query, settings, page)
            logger.info("Сканирую HH: query=%s page=%s", query, page + 1)
            html_text = fetch_html(session, url, settings.request_timeout_seconds)
            soup = BeautifulSoup(html_text, "html.parser")
            cards = find_vacancy_cards(soup)
            if not cards:
                logger.info("HH не вернул карточки вакансий для query=%s page=%s", query, page + 1)
                break

            new_on_page = 0
            for card in cards:
                lead = parse_card(card)
                if not lead:
                    continue
                if storage.has_seen(lead.vacancy_id):
                    logger.info("Пропускаю дубль HH-вакансии: %s", lead.url)
                    continue

                leads.append(lead)
                storage.mark_seen(lead)
                new_on_page += 1
                if len(leads) >= settings.max_leads_per_run:
                    logger.info("Достигнут лимит HH-лидов за запуск: %s", settings.max_leads_per_run)
                    return leads

            logger.info("HH page done: query=%s page=%s new=%s", query, page + 1, new_on_page)
            if page + 1 < settings.max_pages:
                import time

                time.sleep(settings.delay_seconds)

    return leads


def export_to_csv(leads: list[HHVacancyLead], output_csv: Path) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=(
                "Source",
                "Published_At",
                "Segment",
                "Matched_Role",
                "Title",
                "Company",
                "Salary",
                "Location",
                "URL",
                "Snippet",
            ),
        )
        writer.writeheader()
        for lead in leads:
            writer.writerow(
                {
                    "Source": "HH",
                    "Published_At": lead.published_at,
                    "Segment": lead.segment,
                    "Matched_Role": lead.matched_role,
                    "Title": lead.title,
                    "Company": lead.company,
                    "Salary": lead.salary,
                    "Location": lead.location,
                    "URL": lead.url,
                    "Snippet": lead.snippet,
                }
            )

    logger.info("HH CSV сохранен: %s. Новых лидов: %s", output_csv, len(leads))


def build_bot_message(lead: HHVacancyLead) -> str:
    return (
        "📌 <b>HH ЛИД: вакансия</b>\n\n"
        f"🎯 <b>Роль:</b> {html.escape(lead.matched_role)}\n"
        f"🏷 <b>Сегмент:</b> {html.escape(lead.segment)}\n"
        f"💼 <b>Вакансия:</b> {html.escape(lead.title)}\n"
        f"🏢 <b>Компания:</b> {html.escape(lead.company)}\n"
        f"💰 <b>Зарплата:</b> {html.escape(lead.salary)}\n"
        f"📍 <b>Локация:</b> {html.escape(lead.location)}\n"
        f"📅 <b>Дата:</b> {html.escape(lead.published_at or 'не указана')}\n\n"
        f"💬 <b>Коротко:</b>\n{html.escape(lead.snippet)}"
    )


def build_bot_keyboard(lead: HHVacancyLead) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Открыть вакансию на HH", url=lead.url)]]
    )


async def send_leads_to_bot(leads: list[HHVacancyLead], settings: HHScraperSettings) -> None:
    if not settings.send_to_bot:
        logger.info("HH отправка в бот отключена: HH_SCRAPER_SEND_TO_BOT=false")
        return
    if not leads:
        logger.info("Новых HH-лидов для отправки нет")
        return
    if not settings.tg_lead_bot_token or not settings.my_chat_id:
        logger.warning("Не заполнены TG_LEAD_BOT или MY_CHAT_ID. HH CSV сохранен, отправка в бот пропущена.")
        return
    if settings.dry_run:
        logger.info("DRY_RUN=true. HH-лиды не отправлены в бот. Количество: %s", len(leads))
        return

    bot = Bot(token=settings.tg_lead_bot_token)
    leads_to_send = leads[: settings.max_bot_messages_per_run]
    skipped_count = max(0, len(leads) - len(leads_to_send))
    if skipped_count:
        logger.info(
            "HH найдено %s лидов, в бот отправлю первые %s. Остальные %s останутся в CSV.",
            len(leads),
            len(leads_to_send),
            skipped_count,
        )

    try:
        for index, lead in enumerate(leads_to_send, start=1):
            while True:
                try:
                    await bot.send_message(
                        chat_id=settings.my_chat_id,
                        text=build_bot_message(lead),
                        parse_mode=ParseMode.HTML,
                        reply_markup=build_bot_keyboard(lead),
                        disable_web_page_preview=True,
                    )
                    break
                except TelegramRetryAfter as exc:
                    wait_seconds = int(exc.retry_after) + 3
                    logger.warning("Telegram flood control. Жду %s секунд перед повтором.", wait_seconds)
                    await asyncio.sleep(wait_seconds)

            logger.info("Отправлен HH-лид %s/%s: %s", index, len(leads_to_send), lead.url)
            await asyncio.sleep(settings.bot_send_delay_seconds)
    finally:
        await bot.session.close()


async def run_scraper() -> int:
    settings = load_settings()
    leads = await asyncio.to_thread(scan_hh_sync, settings)
    export_to_csv(leads, settings.output_csv)
    await send_leads_to_bot(leads, settings)
    return len(leads)


if __name__ == "__main__":
    asyncio.run(run_scraper())
