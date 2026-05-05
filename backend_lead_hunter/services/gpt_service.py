import json
import logging
from typing import Any

from openai import AsyncOpenAI

from config import Settings
from schemas import LeadResult


logger = logging.getLogger(__name__)


class GPTService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def is_business_post(self, caption: str) -> bool:
        if not caption.strip():
            return False

        response = await self._client.chat.completions.create(
            model=self._settings.openai_model,
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты фильтр Instagram-контента. Ответь только YES или NO. "
                        "YES, если пост про бизнес, продажи, автоматизацию, ИИ, маркетинг, "
                        "воронки, клиентов, заявки, Директ, CRM, онлайн-школы, экспертный контент, "
                        "запуски, обучение предпринимателей или монетизацию экспертизы. "
                        "NO, если это личный лайфстайл, отпуск, семья, еда, спорт или мемы без бизнес-смысла."
                    ),
                },
                {"role": "user", "content": caption[:4000]},
            ],
        )
        answer = response.choices[0].message.content or "NO"
        return answer.strip().upper().startswith("YES")

    async def analyze_comment(self, comment_text: str, competitor_name: str) -> LeadResult:
        response = await self._client.chat.completions.create(
            model=self._settings.openai_model,
            temperature=0.35,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты AI-Архитектор и эксперт по продажам. Ищешь людей, которым можно предложить "
                        "автоматизацию продаж, Директа, заявок, CRM, воронки или клиентского сервиса через Python/GPT.\n\n"
                        "HOT - явная бизнес-боль или прямой запрос: нужен бот, автоматизация, CRM, воронка, "
                        "продажи, лиды, заявки, Директ, хаос, не успеваем отвечать, теряются клиенты, нужен разбор.\n"
                        "WARM - человек проявил интерес к бизнесовому/обучающему посту: '+', 'курс', 'хочу', "
                        "'интересно', 'в личку', 'можно подробнее', 'сколько стоит', 'отправьте', 'нужно'. "
                        "WARM не является финальным лидом, его профиль будет проверен отдельно.\n"
                        "SKIP - спам, реклама своих услуг, случайные эмодзи, поздравления, общая поддержка без интереса.\n\n"
                        "Для HOT и WARM напиши короткий оффер в стиле vibe coding: экспертно, по-человечески, без официоза. "
                        "Если боли мало, зайди от контекста комментария и предложи показать, как автоматизировать продажи, "
                        "Директ или заявки через GPT.\n\n"
                        'Верни строго JSON: {"status":"HOT/WARM/SKIP","analysis":"...","offer":"..."}'
                    ),
                },
                {
                    "role": "user",
                    "content": f"Имя донора/конкурента: {competitor_name}\nКомментарий: {comment_text}",
                },
            ],
        )
        raw_content = response.choices[0].message.content or "{}"
        data = self._parse_json(raw_content)

        status = str(data.get("status", "SKIP")).upper()
        if status not in {"HOT", "WARM", "SKIP"}:
            status = "SKIP"

        return LeadResult(
            status=status,
            analysis=str(data.get("analysis", "")),
            offer=str(data.get("offer", "")),
        )

    async def is_target_profile(self, profile: dict[str, Any], comment_text: str) -> tuple[bool, str]:
        profile_summary = {
            "username": profile.get("username"),
            "fullName": profile.get("fullName"),
            "biography": profile.get("biography"),
            "followersCount": profile.get("followersCount"),
            "followsCount": profile.get("followsCount"),
            "postsCount": profile.get("postsCount"),
            "isBusinessAccount": profile.get("isBusinessAccount"),
            "businessCategoryName": profile.get("businessCategoryName"),
            "externalUrl": profile.get("externalUrl"),
        }

        response = await self._client.chat.completions.create(
            model=self._settings.openai_model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты фильтр ICP для услуги автоматизации продаж/Директа/заявок через GPT и Python. "
                        "Определи, похож ли Instagram-профиль на целевую аудиторию.\n\n"
                        "TARGET, если это предприниматель, эксперт, консультант, коуч, владелец онлайн-школы, "
                        "продюсер, маркетолог, продажник, агентство, сервисный бизнес, B2B/B2C услуги, обучение, "
                        "личный бренд с коммерческим оффером или аккаунт, где явно есть клиенты/заявки/продажи.\n"
                        "SKIP, если это личный аккаунт без бизнеса, школьник/студент без оффера, пустой профиль, "
                        "мемы, фан-аккаунт, случайный пользователь, сомнительный спам, магазин без признаков "
                        "сложных заявок/воронки или непонятно кто.\n\n"
                        'Верни строго JSON: {"target":true/false,"reason":"..."}'
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Комментарий человека: {comment_text}\n"
                        f"Профиль JSON: {json.dumps(profile_summary, ensure_ascii=False)}"
                    ),
                },
            ],
        )
        raw_content = response.choices[0].message.content or "{}"
        data = self._parse_json(raw_content)
        return bool(data.get("target")), str(data.get("reason", ""))

    def _parse_json(self, raw_content: str) -> dict[str, Any]:
        try:
            data = json.loads(raw_content)
        except json.JSONDecodeError:
            logger.warning("GPT вернул не JSON: %s", raw_content)
            return {}
        return data if isinstance(data, dict) else {}
