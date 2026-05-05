import asyncio
import logging
from typing import Any

import httpx

from config import Settings


logger = logging.getLogger(__name__)


class ApifyClient:
    def __init__(self, settings: Settings, http_client: httpx.AsyncClient) -> None:
        self._settings = settings
        self._http_client = http_client
        self._base_url = "https://api.apify.com/v2"

    async def run_actor_and_get_items(self, actor_id: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
        actor_path = actor_id.replace("/", "~")
        logger.info("🚀 Запускаю Apify актор: %s", actor_id)

        run_response = await self._http_client.post(
            f"{self._base_url}/acts/{actor_path}/runs",
            params={"token": self._settings.apify_token},
            json=payload,
            timeout=60,
        )
        run_response.raise_for_status()
        run_data = run_response.json()["data"]
        run_id = run_data["id"]

        dataset_id = await self._wait_for_success(run_id)
        return await self._get_dataset_items(dataset_id)

    async def _wait_for_success(self, run_id: str) -> str:
        while True:
            response = await self._http_client.get(
                f"{self._base_url}/actor-runs/{run_id}",
                params={"token": self._settings.apify_token},
                timeout=30,
            )
            response.raise_for_status()
            run_data = response.json()["data"]
            status = run_data["status"]

            logger.info("⏳ Apify run %s: статус %s", run_id, status)

            if status == "SUCCEEDED":
                return run_data["defaultDatasetId"]

            if status in {"FAILED", "ABORTED", "TIMED-OUT"}:
                raise RuntimeError(f"Apify run {run_id} завершился со статусом {status}")

            await asyncio.sleep(self._settings.apify_poll_interval_seconds)

    async def _get_dataset_items(self, dataset_id: str) -> list[dict[str, Any]]:
        response = await self._http_client.get(
            f"{self._base_url}/datasets/{dataset_id}/items",
            params={"token": self._settings.apify_token, "clean": "true"},
            timeout=60,
        )
        response.raise_for_status()
        items = response.json()
        logger.info("📦 Получил %s записей из Apify dataset", len(items))
        return items
