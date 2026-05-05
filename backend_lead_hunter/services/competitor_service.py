import logging
from typing import Any

from config import Settings
from services.apify_client import ApifyClient


logger = logging.getLogger(__name__)


class CompetitorService:
    def __init__(self, settings: Settings, apify_client: ApifyClient) -> None:
        self._settings = settings
        self._apify_client = apify_client

    async def find_competitors(self, keywords: list[str], max_competitors: int) -> list[str]:
        donors: list[str] = []

        for username in self._settings.seed_donor_list:
            if len(donors) >= max_competitors:
                return donors
            if username in donors:
                continue
            if await self._seed_donor_is_valid(username):
                logger.info("Добавил донора из SEED_DONORS: @%s", username)
                donors.append(username)

        search_keywords = self._merge_keywords(self._settings.similar_donor_keyword_list, keywords)
        if self._settings.seed_donor_list:
            logger.info(
                "Ищу похожих доноров по SIMILAR_DONOR_KEYWORDS и ключам: %s",
                ", ".join(search_keywords),
            )

        for keyword in search_keywords:
            if len(donors) >= max_competitors:
                return donors

            logger.info("Ищу доноров по ключу: %s", keyword)
            payload = {
                "search": keyword,
                "searchType": "user",
                "resultsLimit": max_competitors * 10,
                "addParentData": False,
            }
            items = await self._apify_client.run_actor_and_get_items(
                self._settings.apify_instagram_search_actor,
                payload,
            )

            for item in items:
                if len(donors) >= max_competitors:
                    return donors

                username = self._extract_username(item)
                followers_count = self._extract_followers_count(item)

                if not username or username in donors:
                    continue

                if not self._followers_are_valid(username, followers_count):
                    continue

                logger.info("Нашел донора: @%s (%s подписчиков)", username, followers_count)
                donors.append(username)

        return donors

    async def _seed_donor_is_valid(self, username: str) -> bool:
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
        if not items:
            logger.info("Пропускаю SEED_DONOR @%s: профиль не найден", username)
            return False

        followers_count = self._extract_followers_count(items[0])
        return self._followers_are_valid(username, followers_count)

    def _followers_are_valid(self, username: str, followers_count: int | None) -> bool:
        if followers_count is None:
            logger.info("Пропускаю @%s: не вижу число подписчиков", username)
            return False

        if followers_count < self._settings.min_donor_followers:
            logger.info(
                "Пропускаю @%s: %s подписчиков, нужно от %s",
                username,
                followers_count,
                self._settings.min_donor_followers,
            )
            return False

        return True

    def _merge_keywords(self, *groups: list[str]) -> list[str]:
        result: list[str] = []
        for group in groups:
            for keyword in group:
                if keyword not in result:
                    result.append(keyword)
        return result

    def _extract_username(self, item: dict[str, Any]) -> str | None:
        value = item.get("username") or item.get("userName") or item.get("handle")
        if isinstance(value, str):
            return value.removeprefix("@").strip()
        return None

    def _extract_followers_count(self, item: dict[str, Any]) -> int | None:
        value = (
            item.get("followersCount")
            or item.get("followers")
            or item.get("followedByCount")
            or item.get("followers_count")
        )
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            digits = "".join(char for char in value if char.isdigit())
            return int(digits) if digits else None
        return None
