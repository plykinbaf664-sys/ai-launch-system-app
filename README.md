# Launch OS

Тестовая система запуска 
Базовая База на ai v1.0


This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.

# AI Launch System

## Что это
Внутренняя система запуска, которую я собираю в AI-first формате.

## Текущий стек
- Next.js
- React
- TypeScript
- pnpm
- Git

## Цель проекта
Пошагово собрать операционную систему запуска:
исследование → оффер → лиды → CRM → оплата → аналитика → автоматизация.

## Текущий этап
Этап 0.
Сейчас настраивается базовая среда и AI-режим работы.

## Что уже готово
- создан проект Next.js
- локальный запуск работает
- понятна базовая структура app/page/layout
- подключён Git

## Базовая структура
- app/ — страницы и маршруты
- components/ — переиспользуемые UI-компоненты
- lib/ — функции, утилиты, данные

## Принцип разработки
Работаем маленькими шагами.
Каждая задача:
1. формулируется отдельно,
2. сначала планируется,
3. потом кодится,
4. потом проверяется вручную,
5. потом фиксируется через commit.
_________________________________________

Цель 4 дня:
Собрать первую рабочую страницу Research Hub со списком гипотез.

Результат дня:
Маршрут /research открывается и показывает 3 тестовые карточки гипотез.

Что я должен понять:
- что такое массив
- как рендерить список через map
- как устроена простая карточка
- как отделять страницу от UI-кусков

__________________________________________


# 📌 Day 7 (03.05.2026) — Research OS v0.2 + Competitor Analysis + Pattern Analyzer

## 🧠 Цель дня

Собрать первый полноценный аналитический контур системы:

* сбор отзывов (Research)
* анализ конкурентов (Market layer)
* генерация выводов (Pattern Analyzer)

---

# ✅ Что реализовано

## 1. Research OS (обновление)

Рабочий модуль сбора отзывов:

* ввод: ниша + позиционирование

* сбор отзывов через API

* структурирование данных по полям:

  * ситуация клиента
  * идеальный результат
  * ожидания
  * оправдания
  * причины отсутствия результата
  * страхи
  * боли
  * предрассудки
  * что уже пробовал

* вывод:

  * таблица отзывов
  * экспорт в CSV

👉 Research OS = слой сырья (что говорят люди)

---

## 2. Competitor Analysis OS (новый модуль)

Добавлен анализ 10 конкурентов:

* 3 крупных
* 3 средних
* 3 нишевых
* 1 дополнительный

По каждому конкуренту собирается:

* имя / бренд
* площадка
* уровень
* позиционирование
* сегмент аудитории
* главное обещание
* дифференциация

### Продукты конкурента:

* название
* тип (курс / консультация / подписка / DFY)
* цена
* описание
* обещание результата

### Дополнительно:

* лид-магниты
* структура воронки
* анализ контента (что набирает просмотры)

👉 Competitor Analysis = слой рынка (как продают)

---

## 3. Pattern Analyzer OS (новый модуль)

Работает на базе:

```text
reviews + competitors
```

Формирует:

* позиционирование эксперта
* 3 платёжеспособных сегмента ЦА
* отстройку от конкурентов
* CJM клиента
* эмоции на каждом этапе
* продуктовую линейку
* усиление продуктов через AI
* структуру воронки

👉 Pattern Analyzer = слой решений (что делать)

---

# 🧩 Архитектура потока

```text
Research → Competitors → Pattern Analyzer
```

---

# 🗄️ Структура хранения

Сущность:

```text
research_sessions
```

Поля:

```text
id
niche
positioning

reviews (json)
competitors (json)

patterns (json)

created_at
```

---

# 🖥️ UI-логика страницы /research

Страница теперь содержит:

1. Форма ввода
2. Таблица отзывов (Research)
3. Таблица конкурентов (Competitor Analysis)
4. Текстовый аналитический блок (Pattern Analyzer)

---

# 🎨 UI/UX изменения

* переход к стилю AI/SaaS интерфейса
* минимализм + аккуратная типографика
* карточная структура
* читаемые таблицы
* Pattern Analyzer оформлен как аналитический отчёт

---

# ⚡ Ключевые принципы

```text
Отзывы = что говорят люди
Конкуренты = как продают
Pattern Analyzer = что делать
```

---

# 🚫 Ограничения

* Neiroclozer не подключён
* нет автоматизации
* нет сложной аналитики
* нет мультистраничной навигации

---

# 🚀 Следующий шаг

## Pattern Analyzer → Positioning OS

На базе patterns:

* финализировать позиционирование
* закрепить сегменты
* перейти к созданию продукта и оффера

---

# 💥 Итог

Собран первый end-to-end аналитический контур:

```text
рынок → данные → анализ → решения
```

Система перестала быть “сборщиком данных” и стала инструментом принятия решений

06.05.2026

• ## Lead Hunter Backend

  В проект добавлен отдельный FastAPI backend для автоматической охоты за лидами в Instagram.

  Папка:

  ```text
  backend_lead_hunter/

  Backend работает отдельно от Next.js-приложения и отвечает за полный pipeline:

  поиск доноров -> выбор постов -> сбор комментариев -> GPT-квалификация -> отправка лидов в Telegram

  ## Что реализовано

  - FastAPI endpoint POST /hunt-leads
  - Web-интерфейс запуска охоты на /
  - Интеграция с Apify:
      - apify/instagram-search-scraper
      - apify/instagram-scraper
      - apify/instagram-comment-scraper
  - Интеграция с OpenAI gpt-4o
  - Telegram-уведомления через отдельного lead-бота
  - Фильтр доноров от 5000 подписчиков
  - Поиск по seed-донорам из .env
  - Поиск похожих доноров по ключевым словам
  - Фильтрация бизнесовых/экспертных постов через GPT
  - Квалификация комментариев в статусы:
      - HOT
      - WARM
      - SKIP
  - Дополнительная проверка профиля для WARM лидов
  - Красивое Telegram-сообщение с готовым оффером
  - Inline-кнопка “Написать в Instagram”
  - Суточная автоохота
  - Автоохота стартует только после ручного запуска кнопкой
  - После перезапуска сервера охота сама не стартует

  ## Антидубли и память

  Добавлено SQLite-хранилище:

  lead_hunter.db

  Оно хранит:

  processed_posts
  processed_comments
  sent_leads

  Зачем это нужно:

  - не отправлять одного и того же лида повторно;
  - не анализировать один и тот же комментарий повторно;
  - не залипать на одних и тех же топ-постах;
  - после перезапуска помнить, что уже обработано.

  Если топовый пост уже был обработан, система берет следующий подходящий пост из последних 12 публикаций донора.

  Файл базы добавлен в .gitignore.

  ## Основные файлы

  backend_lead_hunter/main.py

  Управляет FastAPI, web-интерфейсом, запуском pipeline и scheduler’ом.

  backend_lead_hunter/config.py

  Читает настройки из .env.

  backend_lead_hunter/services/competitor_service.py

  Ищет доноров/конкурентов.

  backend_lead_hunter/services/scraper_service.py

  Собирает посты, комментарии и профили.

  backend_lead_hunter/services/gpt_service.py

  Фильтрует посты, анализирует комментарии, проверяет профили и генерирует офферы.

  backend_lead_hunter/services/tg_service.py

  Отправляет лиды в Telegram.

  backend_lead_hunter/services/storage_service.py

  SQLite-хранилище для dedupe и памяти между запусками.

  ## Env-переменные

  Пример находится в:

  backend_lead_hunter/.env.example

  Основные переменные:

  APIFY_TOKEN=
  OPENAI_API_KEY=

  TG_LEAD_BOT=
  MY_CHAT_ID=

  APIFY_INSTAGRAM_SEARCH_ACTOR=apify/instagram-search-scraper
  APIFY_INSTAGRAM_PROFILE_ACTOR=apify/instagram-scraper
  APIFY_INSTAGRAM_COMMENT_ACTOR=apify/instagram-comment-scraper

  OPENAI_MODEL=gpt-4o
  DRY_RUN=false
  APIFY_POLL_INTERVAL_SECONDS=20

  SEED_DONORS=expert1,expert2,expert3
  SIMILAR_DONOR_KEYWORDS=...
  DEFAULT_KEYWORDS=...

  MIN_DONOR_FOLLOWERS=5000

  AUTO_HUNT_ENABLED=true
  AUTO_HUNT_INTERVAL_HOURS=24
  AUTO_HUNT_START_ON_BOOT=false
  AUTO_HUNT_MAX_DONORS=3
  AUTO_HUNT_MAX_COMMENTS_PER_POST=20

  DATABASE_PATH=lead_hunter.db

  ## Локальный запуск

  Перейти в папку backend:

  cd backend_lead_hunter

  Установить зависимости:

  pip install -r requirements.txt

  Запустить сервер:

  uvicorn main:app --reload

  Открыть интерфейс:

  http://127.0.0.1:8000

  ## Как работает автоохота

  Сервер после перезапуска не запускает охоту сам.

  Сценарий:

  1. Сервер запущен.
  2. Пользователь открывает /.
  3. Нажимает кнопку запуска охоты.
  4. Первая охота стартует сразу.
  5. С этого момента включается суточный отсчет.
  6. Следующая охота запускается примерно через 24 часа.

  Если сервер перезапустить, отсчет сбрасывается. Нужно снова нажать кнопку.

  ## Деплой

  Vercel подходит только для Next.js/frontend.

  Этот FastAPI backend нельзя надежно держать на Vercel, потому что ему нужны:

  - долгий pipeline;
  - фоновые задачи;
  - polling Apify;
  - scheduler;
  - постоянный backend-процесс.

  Рекомендуемая схема:

  Vercel = Next.js frontend
  Railway / Render / VPS = backend_lead_hunter

  Для продакшена на Railway/Render нужно:

  - задеплоить папку backend_lead_hunter;
  - добавить env-переменные;
  - указать start command:

  uvicorn main:app --host 0.0.0.0 --port $PORT

  - для сохранения SQLite использовать persistent disk;
  - либо заменить SQLite на Postgres.

  ## Текущее состояние

  Backend локально проверен:

  - Python compile проходит без ошибок;
  - сервер запускается на http://127.0.0.1:8000;
  - SQLite-таблицы создаются;
  - dedupe по постам/комментариям/лидам подключен;
  - автоохота не стартует сама после ребута;
  - суточный цикл активируется после ручного запуска.

15.05.2026 пересобрал архитектуру папок по веткам для удобства плюс пошаговая схема как теперь с этим работать

Как теперь работать с проектом

  У нас один репозиторий, но внутри него несколько зон:

  neurocloser     нейроклозер
  research-ai     ресерч AI
  leadgen         лидогенератор
  main            основная стабильная версия

  main это база.
  В задачах мы работаем не в main, а в отдельной ветке.

  Главное правило

  Одна задача = одна ветка

  Например:

  neurocloser/improve-first-reply
  research-ai/fix-table
  leadgen/add-filter

  Обычный сценарий

  1. Перейти в main:

  git checkout main

  2. Забрать свежую версию с GitHub:

  git pull

  3. Создать ветку под задачу:

  git checkout -b neurocloser/improve-first-reply

  4. После этого мы работаем в Codex и меняем код.
  5. Проверить, что изменилось:

  git status

  6. Добавить изменения:

  git add .

  Или лучше точечно:

  git add app/api/telegram lib/neiroclozer

  7. Сделать коммит:

  git commit -m "neurocloser: improve first reply"

  8. Запушить ветку на GitHub:

  git push -u origin neurocloser/improve-first-reply

  Что делать на GitHub

  После пуша ветки:

  1. Открываешь GitHub.
  2. Открываешь репозиторий.
  3. Видишь кнопку:

     Compare & pull request

  4. Нажимаешь ее.
  5. Нажимаешь:

     Create pull request

  6. Потом:

     Merge pull request

  7. Потом:

     Confirm merge

  После этого задача попала в main.

  После merge

  На компьютере обновляешь main:

  git checkout main
  git pull

  Теперь можно начинать следующую задачу:

  git checkout -b neurocloser/next-task

  Важно про push

  После работы в ветке нейроклозера ты пушишь только эту ветку:

  git push -u origin neurocloser/improve-first-reply

  main пушить не надо.

  main обновляется после Pull Request на GitHub.
  Потом ты просто делаешь:

  git checkout main
  git pull

  Где смотреть ветки

  Локально:

  git branch

  На GitHub ветка появится только после:

  git push -u origin название-ветки

  Пример для нейроклозера

  Начать задачу:

  git checkout main
  git pull
  git checkout -b neurocloser/improve-first-reply

  После изменений:

  git status
  git add app/api/telegram lib/neiroclozer lib/supabase-rest.ts lib/telegram.ts
  git commit -m "neurocloser: improve first reply"
  git push -u origin neurocloser/improve-first-reply

  Потом GitHub:

  Compare & pull request
  Create pull request
  Merge pull request
  Confirm merge

  Потом локально:

  git checkout main
  git pull

  Самая короткая схема

  main
    -> создать ветку задачи
    -> поработать
    -> commit
    -> push ветки
    -> Pull Request на GitHub
    -> Merge в main
    -> git checkout main
    -> git pull
    -> следующая задача

  Запомнить проще всего так

  main = чистая база
  ветка = место для работы
  push = отправить ветку на GitHub
  pull request = предложить добавить ветку в main
  merge = добавить ветку в main
  pull = забрать свежий main себе

