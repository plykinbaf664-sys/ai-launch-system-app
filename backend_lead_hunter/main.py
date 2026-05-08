import asyncio
import contextlib
import logging
import uuid
from dataclasses import dataclass
from typing import Any

import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from config import get_settings
from schemas import HotLead, HuntRequest, HuntResponse, JobState, ViralPost
from services.apify_client import ApifyClient
from services.competitor_service import CompetitorService
from services.gpt_service import GPTService
from services.scraper_service import ScraperService
from services.storage_service import StorageService
from services.tg_service import TelegramService


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

DEFAULT_UI_KEYWORDS = (
    "автоматизация продаж, продажи в директ, нейросети для бизнеса, чат боты для бизнеса, "
    "воронка продаж, CRM для бизнеса, нейропродавец, ИИ для бизнеса, автоматизация бизнеса, "
    "автоворонка продаж, amocrm, онлайн школа, запуск онлайн школы, инстаграм продажи, "
    "лиды из инстаграм, ИИ ассистент, AI эксперт, бизнес процессы, отдел продаж, "
    "скрипты продаж, обработка заявок, клиентский сервис, директ менеджер"
)

app = FastAPI(title="Instagram Lead Hunter", version="1.0.0")
jobs: dict[str, JobState] = {}
pipeline_lock = asyncio.Lock()
scheduler_task: asyncio.Task[None] | None = None
auto_hunt_armed = False


@dataclass
class PostProcessResult:
    sent_count: int
    is_exhausted: bool
    stopped_by_lead_limit: bool


@app.on_event("startup")
async def start_scheduler() -> None:
    global scheduler_task
    settings = get_settings()
    if not settings.auto_hunt_enabled:
        logger.info("Автозапуск отключен: AUTO_HUNT_ENABLED=false")
        return

    scheduler_task = asyncio.create_task(auto_hunt_scheduler())
    logger.info(
        "Автозапуск включен: каждые %s часов, start_on_boot=%s",
        settings.auto_hunt_interval_hours,
        settings.auto_hunt_start_on_boot,
    )


@app.on_event("shutdown")
async def stop_scheduler() -> None:
    if scheduler_task:
        scheduler_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await scheduler_task


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    return f"""
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Instagram Lead Hunter</title>
  <style>
    :root {{
      --bg: #f6f7f9;
      --panel: #ffffff;
      --text: #17181c;
      --muted: #68707d;
      --line: #d9dee7;
      --accent: #1769e0;
      --accent-dark: #1256b7;
      --bad: #b3261e;
      --good: #12733b;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      background: var(--bg);
      color: var(--text);
      font-family: Arial, sans-serif;
      display: flex;
      justify-content: center;
      padding: 32px 16px;
    }}
    main {{
      width: min(760px, 100%);
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 24px;
      box-shadow: 0 12px 32px rgba(20, 30, 50, 0.08);
    }}
    h1 {{ margin: 0 0 8px; font-size: 28px; line-height: 1.2; }}
    p {{ margin: 0 0 20px; color: var(--muted); line-height: 1.5; }}
    label {{ display: block; margin: 16px 0 6px; font-weight: 700; }}
    textarea, input {{
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 11px 12px;
      font: inherit;
      color: var(--text);
      background: #fff;
    }}
    textarea {{ min-height: 120px; resize: vertical; }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
    }}
    button {{
      margin-top: 20px;
      width: 100%;
      border: 0;
      border-radius: 6px;
      padding: 13px 16px;
      background: var(--accent);
      color: #fff;
      font: inherit;
      font-weight: 700;
      cursor: pointer;
    }}
    button:hover {{ background: var(--accent-dark); }}
    button:disabled {{ opacity: .65; cursor: wait; }}
    .status {{
      margin-top: 18px;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 14px;
      background: #fbfcfe;
      white-space: pre-wrap;
      line-height: 1.5;
    }}
    .ok {{ color: var(--good); }}
    .err {{ color: var(--bad); }}
    a {{ color: var(--accent); }}
    @media (max-width: 640px) {{
      main {{ padding: 18px; }}
      .grid {{ grid-template-columns: 1fr; }}
      h1 {{ font-size: 24px; }}
    }}
  </style>
</head>
<body>
  <main>
    <h1>Instagram Lead Hunter</h1>
    <p>Запуск поиска лидов через Apify, GPT и Telegram. Ключи вводи через запятую или с новой строки.</p>

    <form id="huntForm">
      <label for="keywords">Ключевые слова</label>
      <textarea id="keywords">{DEFAULT_UI_KEYWORDS}</textarea>

      <div class="grid">
        <div>
          <label for="maxCompetitors">Доноров</label>
          <input id="maxCompetitors" type="number" min="1" max="50" value="3">
        </div>
        <div>
          <label for="maxComments">Стартовый лимит комментариев</label>
          <input id="maxComments" type="number" min="1" max="1000" value="100">
        </div>
        <div>
          <label for="maxLeads">Лидов за запуск</label>
          <input id="maxLeads" type="number" min="1" max="100" value="10">
        </div>
      </div>

      <button id="submitButton" type="submit">Запустить охоту</button>
    </form>

    <div id="status" class="status">Готов к запуску.</div>
    <p style="margin-top:16px">Техническая документация: <a href="/docs">/docs</a></p>
  </main>

  <script>
    const form = document.getElementById("huntForm");
    const statusBox = document.getElementById("status");
    const button = document.getElementById("submitButton");
    let timer = null;

    function parseKeywords(value) {{
      return value.split(/[\\n,]+/).map((item) => item.trim()).filter(Boolean);
    }}

    function setStatus(text, kind = "") {{
      statusBox.className = "status " + kind;
      statusBox.textContent = text;
    }}

    async function pollJob(jobId) {{
      const response = await fetch(`/hunt-leads/${{jobId}}`);
      const data = await response.json();
      if (!response.ok) {{
        clearInterval(timer);
        button.disabled = false;
        setStatus(`Задача: ${{jobId}}\\nСтатус: не найдено\\nДетали: ${{data.detail || "Сервер перезапускался, статус этой задачи больше не хранится. Запусти охоту заново."}}`, "err");
        return;
      }}

      setStatus(`Задача: ${{jobId}}\\nСтатус: ${{data.status}}\\nДетали: ${{data.detail}}`);

      if (data.status === "SUCCEEDED") {{
        clearInterval(timer);
        button.disabled = false;
        setStatus(`Задача: ${{jobId}}\\nСтатус: ${{data.status}}\\nДетали: ${{data.detail}}`, "ok");
      }}

      if (data.status === "FAILED" || data.status === "SKIPPED") {{
        clearInterval(timer);
        button.disabled = false;
        setStatus(`Задача: ${{jobId}}\\nСтатус: ${{data.status}}\\nДетали: ${{data.detail}}`, "err");
      }}
    }}

    form.addEventListener("submit", async (event) => {{
      event.preventDefault();
      clearInterval(timer);
      button.disabled = true;
      setStatus("Запускаю pipeline...");

      const payload = {{
        keywords: parseKeywords(document.getElementById("keywords").value),
        max_competitors: Number(document.getElementById("maxCompetitors").value),
        max_comments_per_post: Number(document.getElementById("maxComments").value),
        max_leads: Number(document.getElementById("maxLeads").value),
      }};

      try {{
        const response = await fetch("/hunt-leads", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify(payload),
        }});

        const data = await response.json();
        if (!response.ok) {{
          throw new Error(data.detail || "Не удалось запустить задачу");
        }}

        setStatus(`Задача запущена: ${{data.job_id}}\\n${{data.message}}`);
        timer = setInterval(() => pollJob(data.job_id), 5000);
        await pollJob(data.job_id);
      }} catch (error) {{
        button.disabled = false;
        setStatus(error.message, "err");
      }}
    }});
  </script>
</body>
</html>
"""


@app.post("/hunt-leads", response_model=HuntResponse)
async def hunt_leads(request: HuntRequest, background_tasks: BackgroundTasks) -> HuntResponse:
    settings = get_settings()
    keywords = request.keywords or settings.default_keyword_list

    if not keywords:
        raise HTTPException(status_code=400, detail="Передай keywords или заполни DEFAULT_KEYWORDS в .env")

    job_id = str(uuid.uuid4())
    jobs[job_id] = JobState(status="RUNNING", detail="Охота за лидами запущена")
    arm_auto_hunt()
    background_tasks.add_task(run_pipeline, job_id, request, keywords, "manual")

    return HuntResponse(
        job_id=job_id,
        status="RUNNING",
        message="Охота запущена в фоне. Ежедневный автозапуск активирован от этого момента.",
    )


@app.get("/hunt-leads/{job_id}", response_model=JobState)
async def get_job_state(job_id: str) -> JobState:
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return job


async def auto_hunt_scheduler() -> None:
    settings = get_settings()

    if settings.auto_hunt_start_on_boot:
        arm_auto_hunt()
        await schedule_auto_hunt("auto-start")

    while True:
        await asyncio.sleep(settings.auto_hunt_interval_hours * 60 * 60)
        if not auto_hunt_armed:
            logger.info("Автоохота ждет ручного запуска кнопкой")
            continue
        await schedule_auto_hunt("auto-daily")


async def schedule_auto_hunt(source: str) -> str:
    settings = get_settings()
    job_id = str(uuid.uuid4())
    jobs[job_id] = JobState(status="RUNNING", detail=f"Автоохота запущена: {source}")
    request = HuntRequest(
        keywords=[],
        max_competitors=settings.auto_hunt_max_donors,
        max_comments_per_post=settings.auto_hunt_max_comments_per_post,
        max_leads=settings.auto_hunt_max_leads,
    )
    asyncio.create_task(run_pipeline(job_id, request, settings.default_keyword_list, source))
    logger.info("Создана автоохота %s: %s", source, job_id)
    return job_id


def arm_auto_hunt() -> None:
    global auto_hunt_armed
    if not auto_hunt_armed:
        auto_hunt_armed = True
        logger.info("Ежедневная автоохота активирована ручным запуском")


async def run_pipeline(job_id: str, request: HuntRequest, keywords: list[str], source: str) -> None:
    if pipeline_lock.locked():
        jobs[job_id] = JobState(
            status="SKIPPED",
            detail="Предыдущая охота еще идет. Новый запуск пропущен, чтобы не запускать процессы параллельно.",
        )
        logger.info("Pipeline %s пропущен: уже идет другая охота", job_id)
        return

    async with pipeline_lock:
        await _run_pipeline_unlocked(job_id, request, keywords, source)


async def _run_pipeline_unlocked(job_id: str, request: HuntRequest, keywords: list[str], source: str) -> None:
    settings = get_settings()
    sent_count = 0

    try:
        async with httpx.AsyncClient() as http_client:
            apify_client = ApifyClient(settings, http_client)
            gpt_service = GPTService(settings)
            tg_service = TelegramService(settings)
            storage_service = StorageService(settings)
            competitor_service = CompetitorService(settings, apify_client)
            scraper_service = ScraperService(settings, apify_client, gpt_service)

            logger.info("Pipeline стартовал. Источник: %s. Ключи: %s", source, ", ".join(keywords))
            competitors = await competitor_service.find_competitors(
                keywords=keywords,
                max_competitors=request.max_competitors,
            )
            logger.info("Найдено доноров: %s", len(competitors))

            for competitor_username in competitors:
                target_posts = await scraper_service.find_target_posts(
                    competitor_username,
                    is_post_processed=storage_service.has_processed_post,
                )
                for post in target_posts:
                    if storage_service.has_processed_post(post.url):
                        logger.info("Пропускаю уже обработанный пост: %s", post.url)
                        continue

                    post_result = await process_post(
                        post=post,
                        max_comments=request.max_comments_per_post,
                        max_leads_left=request.max_leads - sent_count,
                        comment_fetch_hard_limit=settings.comment_fetch_hard_limit,
                        comment_fetch_growth_factor=settings.comment_fetch_growth_factor,
                        scraper_service=scraper_service,
                        gpt_service=gpt_service,
                        tg_service=tg_service,
                        storage_service=storage_service,
                    )
                    sent_count += post_result.sent_count
                    storage_service.mark_processed_post(
                        post_url=post.url,
                        donor_username=post.competitor_username,
                        comments_count=post.comments_count,
                        status="DONE" if post_result.is_exhausted else "IN_PROGRESS",
                    )
                    if sent_count >= request.max_leads:
                        logger.info("Достигнут лимит лидов за запуск: %s", request.max_leads)
                        break

                if sent_count >= request.max_leads:
                    break

        jobs[job_id] = JobState(
            status="SUCCEEDED",
            detail=f"Pipeline завершен. Лидов отправлено: {sent_count}. Лимит: {request.max_leads}",
        )
        logger.info("Pipeline завершен. Лидов отправлено: %s. Лимит: %s", sent_count, request.max_leads)
    except Exception as exc:
        logger.exception("Pipeline упал с ошибкой")
        jobs[job_id] = JobState(status="FAILED", detail=str(exc))


async def process_post(
    post: ViralPost,
    max_comments: int,
    max_leads_left: int,
    comment_fetch_hard_limit: int,
    comment_fetch_growth_factor: int,
    scraper_service: ScraperService,
    gpt_service: GPTService,
    tg_service: TelegramService,
    storage_service: StorageService,
) -> PostProcessResult:
    sent_count = 0
    is_exhausted = False
    stopped_by_lead_limit = False
    if max_leads_left <= 0:
        return PostProcessResult(sent_count=0, is_exhausted=False, stopped_by_lead_limit=True)

    fetch_limit = max(1, max_comments)
    hard_limit = max(fetch_limit, comment_fetch_hard_limit)
    growth_factor = max(2, comment_fetch_growth_factor)

    while True:
        comments = await scraper_service.get_comments(post.url, fetch_limit)
        new_comments_seen = 0

        for comment in comments:
            if sent_count >= max_leads_left:
                logger.info("Лимит лидов для текущего запуска достигнут, останавливаю анализ поста")
                stopped_by_lead_limit = True
                break

            username = extract_comment_username(comment)
            comment_text = extract_comment_text(comment)

            if not username or not comment_text:
                continue

            comment_id = extract_comment_id(comment)
            comment_key = storage_service.comment_key(post.url, username, comment_text, comment_id)
            if storage_service.has_processed_comment(comment_key):
                logger.info("Пропускаю уже обработанный коммент @%s", username)
                continue

            new_comments_seen += 1

            if username.lower() == post.competitor_username.lower():
                logger.info("Пропускаю комментарий автора поста @%s", username)
                storage_service.mark_processed_comment(comment_key, post.url, username, "SKIP")
                continue

            logger.info("Анализирую коммент @%s: %s", username, comment_text[:120])
            result = await gpt_service.analyze_comment(
                comment_text=comment_text,
                competitor_name=post.competitor_full_name or post.competitor_username,
            )

            if result.status not in {"HOT", "WARM"}:
                logger.info("Коммент @%s не лид", username)
                storage_service.mark_processed_comment(comment_key, post.url, username, result.status)
                continue

            if result.status == "WARM":
                profile = await scraper_service.get_profile(username)
                if not profile:
                    logger.info("Пропускаю WARM @%s: профиль не найден", username)
                    storage_service.mark_processed_comment(comment_key, post.url, username, "WARM_PROFILE_NOT_FOUND")
                    continue

                is_target, reason = await gpt_service.is_target_profile(profile, comment_text)
                if not is_target:
                    logger.info("Пропускаю WARM @%s: не ЦА. %s", username, reason)
                    storage_service.mark_processed_comment(comment_key, post.url, username, "WARM_NOT_TARGET")
                    continue

                result.analysis = f"{result.analysis}\n\nПрофиль ЦА: да. {reason}"

            lead = HotLead(
                status=result.status,
                username=username,
                profile_url=f"https://www.instagram.com/{username}/",
                comment_text=comment_text,
                post_url=post.url,
                competitor_username=post.competitor_username,
                competitor_full_name=post.competitor_full_name,
                analysis=result.analysis,
                offer=result.offer,
            )
            if storage_service.has_sent_lead(lead):
                logger.info("Пропускаю дубль лида @%s", username)
                storage_service.mark_processed_comment(comment_key, post.url, username, f"{result.status}_DUPLICATE")
                continue

            if storage_service.has_sent_username(username):
                logger.info("Пропускаю уже отправленного пользователя @%s", username)
                storage_service.mark_processed_comment(
                    comment_key,
                    post.url,
                    username,
                    f"{result.status}_USER_DUPLICATE",
                )
                continue

            await tg_service.send_hot_lead(lead)
            storage_service.mark_sent_lead(lead)
            storage_service.mark_processed_comment(comment_key, post.url, username, result.status)
            sent_count += 1

        if stopped_by_lead_limit:
            break

        if len(comments) < fetch_limit:
            is_exhausted = True
            break

        if new_comments_seen == 0:
            logger.info("В лимите %s не осталось новых комментариев, расширяю сбор", fetch_limit)

        if fetch_limit >= hard_limit:
            logger.info("Достигнут защитный лимит комментариев на пост: %s", hard_limit)
            is_exhausted = post.comments_count <= hard_limit
            break

        next_fetch_limit = min(fetch_limit * growth_factor, hard_limit)
        logger.info(
            "Лидов по посту пока %s, расширяю сбор комментариев: %s -> %s",
            sent_count,
            fetch_limit,
            next_fetch_limit,
        )
        fetch_limit = next_fetch_limit

    return PostProcessResult(
        sent_count=sent_count,
        is_exhausted=is_exhausted,
        stopped_by_lead_limit=stopped_by_lead_limit,
    )


def extract_comment_username(comment: dict[str, Any]) -> str | None:
    owner = comment.get("owner") if isinstance(comment.get("owner"), dict) else {}
    user = comment.get("user") if isinstance(comment.get("user"), dict) else {}
    raw_username = (
        comment.get("ownerUsername")
        or comment.get("username")
        or owner.get("username")
        or user.get("username")
    )
    if isinstance(raw_username, str):
        return raw_username.removeprefix("@").strip()
    return None


def extract_comment_text(comment: dict[str, Any]) -> str | None:
    raw_text = comment.get("text") or comment.get("comment") or comment.get("caption")
    if isinstance(raw_text, str):
        return raw_text.strip()
    return None


def extract_comment_id(comment: dict[str, Any]) -> str | None:
    for key in ("id", "commentId", "pk", "shortCode"):
        raw_value = comment.get(key)
        if isinstance(raw_value, str) and raw_value.strip():
            return raw_value.strip()
        if isinstance(raw_value, int):
            return str(raw_value)
    return None
