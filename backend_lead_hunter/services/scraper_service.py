import logging
from collections.abc import Callable
from typing import Any

from config import Settings
from schemas import ViralPost
from services.apify_client import ApifyClient
from services.gpt_service import GPTService


logger = logging.getLogger(__name__)


class ScraperService:
    def __init__(
        self,
        settings: Settings,
        apify_client: ApifyClient,
        gpt_service: GPTService,
    ) -> None:
        self._settings = settings
        self._apify_client = apify_client
        self._gpt_service = gpt_service

    async def find_target_posts(
        self,
        competitor_username: str,
        is_post_processed: Callable[[str], bool] | None = None,
    ) -> list[ViralPost]:
        logger.info("Собираю последние посты донора @%s", competitor_username)
        payload = {
            "directUrls": [f"https://www.instagram.com/{competitor_username}/"],
            "resultsType": "posts",
            "resultsLimit": self._settings.donor_posts_lookback,
            "addParentData": False,
        }
        items = await self._apify_client.run_actor_and_get_items(
            self._settings.apify_instagram_profile_actor,
            payload,
        )

        posts = [self._normalize_post(item, competitor_username) for item in items]
        posts = [post for post in posts if post.url]
        top_posts = sorted(posts, key=lambda post: post.comments_count, reverse=True)

        target_posts: list[ViralPost] = []
        for post in top_posts:
            if is_post_processed and is_post_processed(post.url):
                logger.info("Пост уже был обработан раньше, ищу следующий: %s", post.url)
                continue

            logger.info(
                "Проверяю пост @%s с %s комментариями: %s",
                competitor_username,
                post.comments_count,
                post.url,
            )
            is_business = await self._gpt_service.is_business_post(post.caption)
            if is_business:
                logger.info("Пост экспертный, беру в работу: %s", post.url)
                target_posts.append(post)
            else:
                logger.info("Пост не похож на бизнесовый, пропускаю: %s", post.url)

        return target_posts

    async def get_comments(self, post_url: str, max_comments: int) -> list[dict[str, Any]]:
        logger.info("Собираю комментарии к посту: %s", post_url)
        payload = {
            "directUrls": [post_url],
            "resultsLimit": max_comments,
        }
        return await self._apify_client.run_actor_and_get_items(
            self._settings.apify_instagram_comment_actor,
            payload,
        )

    async def get_profile(self, username: str) -> dict[str, Any] | None:
        logger.info("Проверяю профиль потенциального лида @%s", username)
        payload = {
            "directUrls": [f"https://www.instagram.com/{username}/"],
            "resultsType": "details",
            "resultsLimit": 1,
            "addParentData": False,
        }
        items = await self._apify_client.run_actor_and_get_items(
            self._settings.apify_instagram_profile_actor,
            payload,
        )
        return items[0] if items else None

    def _normalize_post(self, item: dict[str, Any], competitor_username: str) -> ViralPost:
        return ViralPost(
            competitor_username=competitor_username,
            competitor_full_name=item.get("ownerFullName") or item.get("fullName"),
            url=item.get("url") or item.get("shortCodeUrl") or "",
            caption=item.get("caption") or item.get("description") or "",
            comments_count=self._as_int(item.get("commentsCount") or item.get("comments")),
        )

    def _as_int(self, value: Any) -> int:
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            digits = "".join(char for char in value if char.isdigit())
            return int(digits) if digits else 0
        return 0
