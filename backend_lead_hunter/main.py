import asyncio
import contextlib
import logging
import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

from config import get_settings
from hh_html_scraper import run_scraper as run_hh_scraper
from schemas import HotLead, HuntRequest, HuntResponse, JobState, ViralPost
from services.apify_client import ApifyClient
from services.competitor_service import CompetitorService
from services.gpt_service import GPTService
from services.scraper_service import ScraperService
from services.storage_service import StorageService
from services.tg_service import TelegramService
from telegram_public_web_scraper import run_scraper as run_telegram_public_web_scraper


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
hh_pipeline_lock = asyncio.Lock()
telegram_pipeline_lock = asyncio.Lock()
scheduler_task: asyncio.Task[None] | None = None
hh_scheduler_task: asyncio.Task[None] | None = None
auto_hunt_armed = False


@dataclass
class PostProcessResult:
    sent_count: int
    is_exhausted: bool
    stopped_by_lead_limit: bool


@app.on_event("startup")
async def start_scheduler() -> None:
    global scheduler_task, hh_scheduler_task
    settings = get_settings()
    if settings.auto_hunt_enabled:
        scheduler_task = asyncio.create_task(auto_hunt_scheduler())
        logger.info(
            "Автозапуск Instagram включен: каждые %s часов, start_on_boot=%s",
            settings.auto_hunt_interval_hours,
            settings.auto_hunt_start_on_boot,
        )
    else:
        logger.info("Автозапуск Instagram отключен: AUTO_HUNT_ENABLED=false")

    if hh_auto_enabled():
        hh_scheduler_task = asyncio.create_task(hh_auto_scheduler())
        logger.info("HH автозапуск включен: каждые %s часов", hh_auto_interval_hours())
    else:
        logger.info("HH автозапуск отключен: HH_SCRAPER_AUTO_ENABLED=false")


@app.on_event("shutdown")
async def stop_scheduler() -> None:
    if scheduler_task:
        scheduler_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await scheduler_task
    if hh_scheduler_task:
        hh_scheduler_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await hh_scheduler_task


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    return f"""
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Leadgen Command Center</title>
  <style>
    :root {{
      --bg: #080808;
      --panel: rgba(17,17,17,.72);
      --text: #ffffff;
      --muted: #888888;
      --line: rgba(0,240,255,.18);
      --accent: #00f0ff;
      --accent-soft: rgba(0,240,255,.12);
      --bad: #ff5e7a;
      --good: #00ff99;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      background:
        radial-gradient(circle at 20% 10%, rgba(0,240,255,.08), transparent 18%),
        radial-gradient(circle at 85% 20%, rgba(0,240,255,.05), transparent 18%),
        radial-gradient(circle at 58% 92%, rgba(0,255,153,.045), transparent 22%),
        linear-gradient(180deg, #080808 0%, #0a0a0a 100%);
      color: var(--text);
      font-family: Inter, Arial, sans-serif;
      padding: 34px 18px 42px;
      overflow-x: hidden;
    }}
    body::before {{
      position: fixed;
      inset: 0;
      pointer-events: none;
      content: "";
      background-image:
        linear-gradient(rgba(255,255,255,.018) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,.018) 1px, transparent 1px);
      background-size: 32px 32px;
      mask-image: linear-gradient(180deg, black, transparent 92%);
    }}
    body::after {{
      position: fixed;
      inset: 0;
      pointer-events: none;
      content: "";
      background: repeating-linear-gradient(180deg, rgba(255,255,255,.022) 0, rgba(255,255,255,.022) 1px, transparent 1px, transparent 7px);
      opacity: .18;
    }}
    main {{
      position: relative;
      z-index: 2;
      width: min(1180px, 100%);
      margin: 0 auto;
      background: var(--panel);
      border: 1px solid rgba(0,240,255,.18);
      padding: 34px;
      box-shadow: 0 0 32px rgba(0,240,255,.14), 0 12px 40px rgba(0,0,0,.45);
      backdrop-filter: blur(14px);
      clip-path: polygon(0 0, calc(100% - 28px) 0, 100% 28px, 100% 100%, 0 100%);
    }}
    h1 {{ margin: 0 0 14px; font-size: 64px; line-height: .92; font-weight: 900; letter-spacing: 0; text-transform: uppercase; }}
    p {{ margin: 0 0 20px; color: #c5d4d7; line-height: 1.6; }}
    label {{ display: block; margin: 16px 0 8px; color: var(--accent); font-family: Consolas, monospace; font-size: 12px; font-weight: 700; letter-spacing: 0; text-transform: uppercase; }}
    textarea, input {{
      width: 100%;
      border: 1px solid rgba(0,240,255,.18);
      border-radius: 0;
      padding: 11px 12px;
      font: inherit;
      color: var(--text);
      outline: none;
      background: rgba(255,255,255,.035);
      box-shadow: inset 0 0 20px rgba(0,240,255,.035);
    }}
    textarea:focus, input:focus {{
      border-color: rgba(0,240,255,.45);
      box-shadow: 0 0 24px rgba(0,240,255,.14), inset 0 0 20px rgba(0,240,255,.06);
    }}
    textarea {{ min-height: 120px; resize: vertical; }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
    }}
    button {{
      position: relative;
      overflow: hidden;
      margin-top: 20px;
      width: 100%;
      border: 1px solid rgba(0,240,255,.28);
      border-radius: 0;
      padding: 13px 16px;
      background: linear-gradient(90deg, rgba(0,240,255,.22), rgba(0,255,153,.12));
      color: #fff;
      font: 800 13px Consolas, monospace;
      letter-spacing: 0;
      text-transform: uppercase;
      cursor: pointer;
      transition: transform 220ms ease, box-shadow 220ms ease, border-color 220ms ease;
    }}
    button::after, .download::after {{
      position: absolute;
      inset: 0;
      content: "";
      background: linear-gradient(120deg, transparent, rgba(255,255,255,.24), transparent);
      transform: translateX(-120%);
      transition: transform 700ms ease;
    }}
    button:hover, .download:hover {{
      transform: translateY(-2px);
      border-color: rgba(0,240,255,.46);
      box-shadow: 0 0 36px rgba(0,240,255,.2);
    }}
    button:hover::after, .download:hover::after {{
      transform: translateX(120%);
    }}
    button:disabled {{ opacity: .65; cursor: wait; }}
    .actions {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
    }}
    .secondary {{
      background: rgba(255,255,255,.045);
    }}
    .download {{
      position: relative;
      overflow: hidden;
      display: block;
      margin-top: 12px;
      width: 100%;
      border-radius: 0;
      border: 1px solid rgba(0,240,255,.18);
      padding: 12px 16px;
      text-align: center;
      text-decoration: none;
      font: 800 13px Consolas, monospace;
      letter-spacing: 0;
      text-transform: uppercase;
      color: var(--text);
      background: rgba(255,255,255,.035);
    }}
    .status {{
      margin-top: 22px;
      border: 1px solid rgba(0,240,255,.18);
      padding: 16px;
      background: rgba(17,17,17,.72);
      box-shadow: 0 0 32px rgba(0,240,255,.14);
      backdrop-filter: blur(14px);
      white-space: pre-wrap;
      line-height: 1.5;
      color: #d7fbff;
    }}
    .ok {{ color: var(--good); }}
    .err {{ color: var(--bad); }}
    .source-grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 14px;
      margin-top: 22px;
    }}
    .source-card {{
      min-height: 154px;
      border: 1px solid rgba(0,240,255,.18);
      padding: 18px;
      background: rgba(17,17,17,.72);
      box-shadow: 0 0 32px rgba(0,240,255,.14), 0 12px 40px rgba(0,0,0,.45);
      backdrop-filter: blur(14px);
      transition: transform 220ms ease, box-shadow 220ms ease, border-color 220ms ease;
    }}
    .source-card:hover {{
      transform: translateY(-4px);
      border-color: rgba(0,240,255,.42);
      box-shadow: 0 0 42px rgba(0,240,255,.2), 0 16px 52px rgba(0,0,0,.55);
    }}
    .source-card strong {{
      display: block;
      margin-top: 18px;
      font-size: 40px;
      line-height: 1;
    }}
    .source-card p {{
      min-height: 42px;
      margin: 10px 0 14px;
      color: #b3b3b3;
      line-height: 1.45;
    }}
    .panel-label {{
      display: flex;
      justify-content: space-between;
      gap: 16px;
      color: var(--accent);
      font: 700 12px Consolas, monospace;
      letter-spacing: 0;
      text-transform: uppercase;
    }}
    .live {{ color: var(--good); }}
    .signal {{
      height: 6px;
      overflow: hidden;
      background: rgba(255,255,255,.07);
    }}
    .signal span {{
      display: block;
      height: 100%;
      background: linear-gradient(90deg, var(--accent), var(--good));
      box-shadow: 0 0 18px rgba(0,240,255,.52);
    }}
    .cursor-glow {{
      position: fixed;
      z-index: 1;
      width: 380px;
      height: 380px;
      border-radius: 50%;
      pointer-events: none;
      background: radial-gradient(circle, rgba(0,240,255,.12) 0%, rgba(0,240,255,.05) 24%, transparent 68%);
      filter: blur(20px);
      transform: translate3d(-999px, -999px, 0);
      transition: transform 120ms linear;
    }}
    .ai-entity {{
      position: fixed;
      z-index: 4;
      width: 148px;
      height: 108px;
      pointer-events: none;
      transform: translate3d(72vw, 20vh, 0);
      transform-origin: 50% 50%;
      transition: transform 3600ms cubic-bezier(.19, 1, .22, 1), filter 240ms ease;
    }}
    .ai-core, .ai-focus, .ai-ring, .ai-scan, .ai-tail {{
      position: absolute;
    }}
    .ai-core {{
      inset: 18px 34px 12px 28px;
      border-radius: 52% 48% 58% 42%;
      background:
        radial-gradient(circle at 62% 40%, rgba(255,255,255,.92), rgba(0,240,255,.48) 18%, transparent 38%),
        radial-gradient(circle at 34% 62%, rgba(0,255,153,.28), transparent 48%),
        radial-gradient(circle, rgba(0,240,255,.22), transparent 68%);
      box-shadow: 0 0 64px rgba(0,240,255,.48), 0 0 110px rgba(0,255,153,.12);
      animation: entity-float 5s ease-in-out infinite;
    }}
    .ai-core::before, .ai-core::after {{
      position: absolute;
      content: "";
      border-radius: 50%;
      background: rgba(255,255,255,.8);
      box-shadow: 0 0 18px rgba(255,255,255,.62), 0 0 32px rgba(0,240,255,.52);
    }}
    .ai-core::before {{
      width: 10px;
      height: 10px;
      right: 28px;
      top: 24px;
    }}
    .ai-core::after {{
      width: 6px;
      height: 6px;
      right: 45px;
      top: 36px;
      opacity: .75;
    }}
    .ai-focus {{
      width: 42px;
      height: 26px;
      right: 26px;
      top: 38px;
      border-radius: 50%;
      background: radial-gradient(circle, rgba(255,255,255,.82), rgba(0,240,255,.2) 45%, transparent 72%);
      filter: blur(.4px);
      animation: focus-pulse 2.8s ease-in-out infinite;
    }}
    .ai-ring {{
      inset: 8px 18px 4px 16px;
      border: 1px solid rgba(0,240,255,.42);
      border-radius: 48% 52% 44% 56%;
      animation: rotate 8s linear infinite;
    }}
    .ai-scan {{
      inset: 10px 22px 8px 18px;
      border-radius: 50%;
      border-top: 1px solid rgba(255,255,255,.5);
      animation: scan 2.6s ease-in-out infinite;
    }}
    .ai-tail {{
      left: -16px;
      top: 42px;
      width: 92px;
      height: 38px;
      border-radius: 60% 10% 10% 60%;
      background: linear-gradient(90deg, transparent, rgba(0,240,255,.12), rgba(0,255,153,.08));
      filter: blur(8px);
      animation: tail-breathe 3.4s ease-in-out infinite;
    }}
    main > p:nth-of-type(2) {{ display: none; }}
    @keyframes rotate {{ to {{ rotate: 360deg; }} }}
    @keyframes entity-float {{
      0%, 100% {{ transform: translateY(0) scale(1); }}
      50% {{ transform: translateY(-10px) scale(1.04); }}
    }}
    @keyframes focus-pulse {{
      0%, 100% {{ transform: scale(.88); opacity: .58; }}
      50% {{ transform: scale(1.12); opacity: 1; }}
    }}
    @keyframes tail-breathe {{
      0%, 100% {{ transform: scaleX(.78); opacity: .36; }}
      50% {{ transform: scaleX(1.12); opacity: .68; }}
    }}
    @keyframes scan {{
      0%, 100% {{ transform: rotate(0deg) scale(.86); opacity: .3; }}
      50% {{ transform: rotate(180deg) scale(1.1); opacity: .86; }}
    }}
    a {{ color: var(--accent); }}
    @media (max-width: 640px) {{
      body {{ padding: 18px; }}
      main {{ padding: 22px; }}
      .grid {{ grid-template-columns: 1fr; }}
      .actions {{ grid-template-columns: 1fr; }}
      .source-grid {{ grid-template-columns: 1fr; }}
      h1 {{ font-size: 42px; }}
    }}
  </style>
</head>
<body>
  <div class="cursor-glow" id="cursorGlow"></div>
  <div class="ai-entity" id="aiEntity" aria-hidden="true">
    <div class="ai-tail"></div>
    <div class="ai-core"></div>
    <div class="ai-focus"></div>
    <div class="ai-ring"></div>
    <div class="ai-scan"></div>
  </div>
  <main>
    <p class="panel-label"><span>LEADGEN OPERATING SYSTEM</span><span class="live">ACTIVE</span></p>
    <h1>Neural Lead Command Center</h1>
    <p>Control panel for Instagram, Telegram and HeadHunter lead capture. Strict filtering, dedupe memory, CSV export and Telegram delivery stay connected to the same backend routes.</p>
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

      <div class="actions">
        <button id="submitButton" type="submit">Запустить охоту</button>
        <button id="telegramButton" class="secondary" type="button">Лиды ТГ</button>
        <button id="hhButton" class="secondary" type="button">Лиды HH</button>
      </div>
      <a class="download" href="/download-telegram-leads">Скачать CSV лидов ТГ</a>
      <a class="download" href="/download-hh-leads">Скачать CSV лидов HH</a>
    </form>

    <section class="source-grid" aria-label="Lead sources">
      <article class="source-card">
        <div class="panel-label"><span>Instagram</span><span class="live">LIVE</span></div>
        <strong>IG</strong>
        <p>Donor search, comments, GPT qualification and bot delivery.</p>
        <div class="signal"><span style="width:87%"></span></div>
      </article>
      <article class="source-card">
        <div class="panel-label"><span>Telegram</span><span>SCAN</span></div>
        <strong>TG</strong>
        <p>Public channel scraper with strict vacancy filters and contact extraction.</p>
        <div class="signal"><span style="width:64%"></span></div>
      </article>
      <article class="source-card">
        <div class="panel-label"><span>HeadHunter</span><span>5H LOOP</span></div>
        <strong>HH</strong>
        <p>Fresh vacancy search, 20-result batches and duplicate memory.</p>
        <div class="signal"><span style="width:92%"></span></div>
      </article>
    </section>

    <div id="status" class="status">Готов к запуску.</div>
    <p style="margin-top:16px">Техническая документация: <a href="/docs">/docs</a></p>
  </main>

  <script>
    const form = document.getElementById("huntForm");
    const statusBox = document.getElementById("status");
    const button = document.getElementById("submitButton");
    const telegramButton = document.getElementById("telegramButton");
    const hhButton = document.getElementById("hhButton");
    const cursorGlow = document.getElementById("cursorGlow");
    const aiEntity = document.getElementById("aiEntity");
    let timer = null;
    let waypointIndex = 0;
    const entityWaypoints = [
      {{ x: "72vw", y: "15vh", rotate: "-8deg" }},
      {{ x: "12vw", y: "24vh", rotate: "9deg" }},
      {{ x: "66vw", y: "58vh", rotate: "4deg" }},
      {{ x: "28vw", y: "68vh", rotate: "-12deg" }},
      {{ x: "82vw", y: "36vh", rotate: "7deg" }},
    ];

    document.querySelector('label[for="keywords"]').textContent = "Instagram intent keywords";
    document.querySelector('label[for="maxCompetitors"]').textContent = "Donors";
    document.querySelector('label[for="maxComments"]').textContent = "Comment scan limit";
    document.querySelector('label[for="maxLeads"]').textContent = "Leads per run";
    button.textContent = "Run Instagram";
    telegramButton.textContent = "Run Telegram";
    hhButton.textContent = "Run HH";
    document.querySelector('a[href="/download-telegram-leads"]').textContent = "Download TG CSV";
    document.querySelector('a[href="/download-hh-leads"]').textContent = "Download HH CSV";
    statusBox.textContent = "SYSTEM READY\\nAwaiting command.";

    window.addEventListener("pointermove", (event) => {{
      cursorGlow.style.transform = `translate3d(${{event.clientX - 190}}px, ${{event.clientY - 190}}px, 0)`;
    }});

    function moveEntity() {{
      waypointIndex = (waypointIndex + 1) % entityWaypoints.length;
      const point = entityWaypoints[waypointIndex];
      aiEntity.style.transform = `translate3d(${{point.x}}, ${{point.y}}, 0) rotate(${{point.rotate}})`;
    }}
    moveEntity();
    window.setInterval(moveEntity, 5200);

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
        telegramButton.disabled = false;
        hhButton.disabled = false;
        setStatus(`Задача: ${{jobId}}\\nСтатус: не найдено\\nДетали: ${{data.detail || "Сервер перезапускался, статус этой задачи больше не хранится. Запусти охоту заново."}}`, "err");
        return;
      }}

      setStatus(`Задача: ${{jobId}}\\nСтатус: ${{data.status}}\\nДетали: ${{data.detail}}`);

      if (data.status === "SUCCEEDED") {{
        clearInterval(timer);
        button.disabled = false;
        telegramButton.disabled = false;
        hhButton.disabled = false;
        setStatus(`Задача: ${{jobId}}\\nСтатус: ${{data.status}}\\nДетали: ${{data.detail}}`, "ok");
      }}

      if (data.status === "FAILED" || data.status === "SKIPPED") {{
        clearInterval(timer);
        button.disabled = false;
        telegramButton.disabled = false;
        hhButton.disabled = false;
        setStatus(`Задача: ${{jobId}}\\nСтатус: ${{data.status}}\\nДетали: ${{data.detail}}`, "err");
      }}
    }}

    form.addEventListener("submit", async (event) => {{
      event.preventDefault();
      clearInterval(timer);
      button.disabled = true;
      telegramButton.disabled = true;
      hhButton.disabled = true;
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
        telegramButton.disabled = false;
        hhButton.disabled = false;
        setStatus(error.message, "err");
      }}
    }});

    telegramButton.addEventListener("click", async () => {{
      clearInterval(timer);
      button.disabled = true;
      telegramButton.disabled = true;
      hhButton.disabled = true;
      setStatus("Запускаю сбор лидов из Telegram...");

      try {{
        const response = await fetch("/hunt-telegram-leads", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
        }});

        const data = await response.json();
        if (!response.ok) {{
          throw new Error(data.detail || "Не удалось запустить сбор лидов из Telegram");
        }}

        setStatus(`Задача запущена: ${{data.job_id}}\\n${{data.message}}`);
        timer = setInterval(() => pollJob(data.job_id), 5000);
        await pollJob(data.job_id);
      }} catch (error) {{
        button.disabled = false;
        telegramButton.disabled = false;
        hhButton.disabled = false;
        setStatus(error.message, "err");
      }}
    }});

    hhButton.addEventListener("click", async () => {{
      clearInterval(timer);
      button.disabled = true;
      telegramButton.disabled = true;
      hhButton.disabled = true;
      setStatus("Запускаю сбор лидов с HeadHunter...");

      try {{
        const response = await fetch("/hunt-hh-leads", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
        }});

        const data = await response.json();
        if (!response.ok) {{
          throw new Error(data.detail || "Не удалось запустить сбор лидов с HeadHunter");
        }}

        setStatus(`Задача запущена: ${{data.job_id}}\n${{data.message}}`);
        timer = setInterval(() => pollJob(data.job_id), 5000);
        await pollJob(data.job_id);
      }} catch (error) {{
        button.disabled = false;
        telegramButton.disabled = false;
        hhButton.disabled = false;
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


@app.post("/hunt-hh-leads", response_model=HuntResponse)
async def hunt_hh_leads(background_tasks: BackgroundTasks) -> HuntResponse:
    job_id = str(uuid.uuid4())
    jobs[job_id] = JobState(status="RUNNING", detail="Сбор лидов с HeadHunter запущен")
    background_tasks.add_task(run_hh_pipeline, job_id)

    return HuntResponse(
        job_id=job_id,
        status="RUNNING",
        message="Сбор лидов с HeadHunter запущен в фоне. Результат придет в CSV и Telegram-бота.",
    )


@app.post("/hunt-telegram-leads", response_model=HuntResponse)
async def hunt_telegram_leads(background_tasks: BackgroundTasks) -> HuntResponse:
    job_id = str(uuid.uuid4())
    jobs[job_id] = JobState(status="RUNNING", detail="Сбор лидов из Telegram запущен")
    background_tasks.add_task(run_telegram_pipeline, job_id)

    return HuntResponse(
        job_id=job_id,
        status="RUNNING",
        message="Сбор лидов из Telegram запущен в фоне. Результат придет в CSV и Telegram-бота.",
    )


@app.get("/hunt-leads/{job_id}", response_model=JobState)
async def get_job_state(job_id: str) -> JobState:
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return job


@app.get("/download-hh-leads")
async def download_hh_leads() -> FileResponse:
    output_path = Path(os.getenv("HH_SCRAPER_OUTPUT_CSV", "hh_vacancy_leads.csv"))
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="CSV еще не создан. Сначала нажми кнопку Лиды HH.")

    return FileResponse(
        output_path,
        media_type="text/csv; charset=utf-8",
        filename="hh_vacancy_leads.csv",
    )


@app.get("/download-telegram-leads")
async def download_telegram_leads() -> FileResponse:
    output_path = Path(os.getenv("TG_SCRAPER_OUTPUT_CSV", "telegram_vacancy_leads.csv"))
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="CSV еще не создан. Сначала нажми кнопку Лиды ТГ.")

    return FileResponse(
        output_path,
        media_type="text/csv; charset=utf-8",
        filename="telegram_vacancy_leads.csv",
    )


async def run_hh_pipeline(job_id: str) -> None:
    if hh_pipeline_lock.locked():
        jobs[job_id] = JobState(
            status="SKIPPED",
            detail="Сбор HH-лидов уже идет. Новый запуск пропущен.",
        )
        logger.info("HH pipeline %s пропущен: уже идет другой сбор", job_id)
        return

    async with hh_pipeline_lock:
        try:
            sent_count = await run_hh_scraper()
            jobs[job_id] = JobState(
                status="SUCCEEDED",
                detail=f"Сбор HH-лидов завершен. Найдено и обработано: {sent_count}.",
            )
            logger.info("HH pipeline завершен. Найдено лидов: %s", sent_count)
        except Exception as exc:
            logger.exception("HH pipeline упал с ошибкой")
            jobs[job_id] = JobState(status="FAILED", detail=str(exc))


async def run_telegram_pipeline(job_id: str) -> None:
    if telegram_pipeline_lock.locked():
        jobs[job_id] = JobState(
            status="SKIPPED",
            detail="Сбор Telegram-лидов уже идет. Новый запуск пропущен.",
        )
        logger.info("Telegram pipeline %s пропущен: уже идет другой сбор", job_id)
        return

    async with telegram_pipeline_lock:
        try:
            sent_count = await run_telegram_public_web_scraper()
            jobs[job_id] = JobState(
                status="SUCCEEDED",
                detail=f"Сбор Telegram-лидов завершен. Найдено и обработано: {sent_count}.",
            )
            logger.info("Telegram pipeline завершен. Найдено лидов: %s", sent_count)
        except Exception as exc:
            logger.exception("Telegram pipeline упал с ошибкой")
            jobs[job_id] = JobState(status="FAILED", detail=str(exc))


async def hh_auto_scheduler() -> None:
    while True:
        await asyncio.sleep(hh_auto_interval_hours() * 60 * 60)
        await schedule_hh_hunt("auto-hh")


async def schedule_hh_hunt(source: str) -> str:
    job_id = str(uuid.uuid4())
    jobs[job_id] = JobState(status="RUNNING", detail=f"HH автосбор запущен: {source}")
    asyncio.create_task(run_hh_pipeline(job_id))
    logger.info("Создан HH автосбор %s: %s", source, job_id)
    return job_id


def hh_auto_enabled() -> bool:
    return os.getenv("HH_SCRAPER_AUTO_ENABLED", "true").strip().casefold() in {"1", "true", "yes", "y", "on"}


def hh_auto_interval_hours() -> float:
    raw_value = os.getenv("HH_SCRAPER_AUTO_INTERVAL_HOURS", "5").strip()
    try:
        return max(0.1, float(raw_value))
    except ValueError:
        logger.warning("HH_SCRAPER_AUTO_INTERVAL_HOURS=%s некорректен, использую 5 часов", raw_value)
        return 5.0


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
