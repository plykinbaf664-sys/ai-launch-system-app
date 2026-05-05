import html
import logging

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import Settings
from schemas import HotLead


logger = logging.getLogger(__name__)


class TelegramService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._bot = Bot(token=settings.tg_lead_bot_token)

    async def send_hot_lead(self, lead: HotLead) -> None:
        message = self._build_message(lead)
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Написать в Instagram", url=lead.profile_url)]
            ]
        )

        if self._settings.dry_run:
            logger.info("DRY_RUN=true. Лид не отправлен в Telegram:\n%s", message)
            return

        await self._bot.send_message(
            chat_id=self._settings.my_chat_id,
            text=message,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard,
            disable_web_page_preview=True,
        )
        logger.info("Отправил %s лид в Telegram: @%s", lead.status, lead.username)

    def _build_message(self, lead: HotLead) -> str:
        username = html.escape(lead.username)
        profile_url = html.escape(lead.profile_url)
        pain = html.escape(lead.comment_text)
        analysis = html.escape(lead.analysis)
        offer = html.escape(lead.offer)
        competitor = html.escape(lead.competitor_full_name or lead.competitor_username)
        post_url = html.escape(lead.post_url)

        title = "ГОРЯЧИЙ ЛИД" if lead.status == "HOT" else "ТЕПЛЫЙ ЛИД"
        marker = "🔥" if lead.status == "HOT" else "🟡"

        return (
            f"{marker} <b>{title}</b>\n\n"
            f"👤 <b>Юзер:</b> <a href=\"{profile_url}\">@{username}</a>\n"
            f"🎯 <b>Источник:</b> комментарий у {competitor}\n"
            f"🔗 <b>Пост:</b> <a href=\"{post_url}\">открыть</a>\n\n"
            f"💬 <b>Комментарий:</b>\n{pain}\n\n"
            f"🧠 <b>АНАЛИЗ:</b>\n{analysis}\n\n"
            "⚡ <b>ГОТОВЫЙ ОФФЕР:</b>\n"
            f"<blockquote>{offer}</blockquote>"
        )
