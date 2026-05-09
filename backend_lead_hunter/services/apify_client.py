import asyncio
import logging
from typing import Any

import httpx

from config import Settings


logger = logging.getLogger(__name__)


class ApifyClient:
    _RETRY_STATUS_CODES = {429, 500, 502, 503, 504}
    _MAX_REQUEST_ATTEMPTS = 5

    def __init__(self, settings: Settings, http_client: httpx.AsyncClient) -> None:
        self._settings = settings
        self._http_client = http_client
        self._base_url = "https://api.apify.com/v2"

    async def run_actor_and_get_items(self, actor_id: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
        actor_path = actor_id.replace("/", "~")
        logger.info("Запускаю Apify актор: %s", actor_id)

        run_response = await self._request_with_retries(
            "POST",
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
            response = await self._request_with_retries(
                "GET",
                f"{self._base_url}/actor-runs/{run_id}",
                params={"token": self._settings.apify_token},
                timeout=30,
            )
            response.raise_for_status()
            run_data = response.json()["data"]
            status = run_data["status"]

            logger.info("Apify run %s: статус %s", run_id, status)

            if status == "SUCCEEDED":
                return run_data["defaultDatasetId"]

            if status in {"FAILED", "ABORTED", "TIMED-OUT"}:
                raise RuntimeError(f"Apify run {run_id} завершился со статусом {status}")

            await asyncio.sleep(self._settings.apify_poll_interval_seconds)

    async def _get_dataset_items(self, dataset_id: str) -> list[dict[str, Any]]:
        response = await self._request_with_retries(
            "GET",
            f"{self._base_url}/datasets/{dataset_id}/items",
            params={"token": self._settings.apify_token, "clean": "true"},
            timeout=60,
        )
        response.raise_for_status()
        items = response.json()
        logger.info("Получил %s записей из Apify dataset", len(items))
        return items

    async def _request_with_retries(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        last_error: Exception | None = None

        for attempt in range(1, self._MAX_REQUEST_ATTEMPTS + 1):
            try:
                response = await self._http_client.request(method, url, **kwargs)
                if response.status_code not in self._RETRY_STATUS_CODES:
                    return response

                last_error = httpx.HTTPStatusError(
                    f"Apify temporary HTTP {response.status_code}",
                    request=response.request,
                    response=response,
                )
                logger.warning(
                    "Apify временно вернул HTTP %s. Попытка %s/%s",
                    response.status_code,
                    attempt,
                    self._MAX_REQUEST_ATTEMPTS,
                )
            except (httpx.ConnectError, httpx.ReadError, httpx.WriteError, httpx.TimeoutException) as exc:
                last_error = exc
                logger.warning(
                    "Временная ошибка запроса к Apify: %s. Попытка %s/%s",
                    exc,
                    attempt,
                    self._MAX_REQUEST_ATTEMPTS,
                )

            if attempt < self._MAX_REQUEST_ATTEMPTS:
                await asyncio.sleep(min(2**attempt, 30))

        if last_error:
            raise last_error

        raise RuntimeError("Не удалось выполнить запрос к Apify")
