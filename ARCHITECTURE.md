# Current Architecture

This document describes the current project structure without changing the code layout.

## Repository Model

The project is one git repository with several product areas inside it:

```text
ai-launch-system-app/
  app/
  components/
  lib/
  supabase/
  backend_lead_hunter/
```

Git branches are split by project area. See `PROJECT_AREAS.md`.

## Runtime Layers

### 1. Next.js Application

Main stack:

```text
Next.js 16.2.2
React 19.2.4
TypeScript
Tailwind CSS 4
```

Main folders:

```text
app/          Next.js App Router pages and API routes
components/   React UI components
lib/          Server-side helpers and integration logic
public/       Static assets
```

Important entry points:

```text
app/layout.tsx       Root layout
app/page.tsx         Home page
app/research/page.tsx Research AI page
app/test/page.tsx    Test page
```

### 2. Next.js API Routes

API routes live inside `app/api/`.

```text
app/api/telegram/webhook/route.ts
app/api/gift/[leadId]/route.ts
app/api/cron/gift-followups/route.ts
app/api/research-reviews/route.ts
app/api/research-competitors/route.ts
app/api/test/route.ts
```

Current responsibilities:

```text
telegram/webhook       Receives Telegram updates and drives Neurocloser flow
gift/[leadId]          Tracks gift link opening and redirects to gift URL
cron/gift-followups    Sends scheduled gift follow-up messages
research-reviews       Generates market/review research via OpenAI
research-competitors   Generates competitor analysis via OpenAI
test                   Test endpoint for Neurocloser prompt/reply flow
```

### 3. Shared Next.js Libraries

Shared integration code lives in `lib/`.

```text
lib/supabase-rest.ts
lib/telegram.ts
lib/neiroclozer/generate-reply.ts
lib/neiroclozer/prompt-builder.ts
```

Responsibilities:

```text
supabase-rest.ts          Supabase REST access for profiles, leads, offers, FAQ, objections, messages
telegram.ts               Telegram webhook validation, message parsing, and sending messages
generate-reply.ts         Anthropic API call for Neurocloser replies
prompt-builder.ts         Builds the Neurocloser prompt from expert, lead, and message context
```

## Product Areas

### Neurocloser

Purpose:

```text
Telegram-based AI closer flow for incoming leads.
```

Main files:

```text
app/api/telegram/webhook/route.ts
app/api/gift/[leadId]/route.ts
app/api/cron/gift-followups/route.ts
app/api/test/route.ts
lib/neiroclozer/
lib/supabase-rest.ts
lib/telegram.ts
supabase/sql/
```

Main flow:

```text
Telegram update
  -> app/api/telegram/webhook/route.ts
  -> parse and validate message
  -> load or create lead in Supabase
  -> load expert context from Supabase
  -> build prompt with lib/neiroclozer/prompt-builder.ts
  -> generate reply with Anthropic
  -> send reply through Telegram API
  -> store messages and lead state in Supabase
```

External systems:

```text
Telegram Bot API
Supabase REST API
Anthropic Messages API
```

### Research AI

Purpose:

```text
Research page for review analysis, competitor analysis, and pattern extraction.
```

Main files:

```text
app/research/page.tsx
components/ReviewsTable.tsx
components/research/CompetitorAnalysis.tsx
components/research/PatternAnalyzer.tsx
components/research/types.ts
app/api/research-reviews/route.ts
app/api/research-competitors/route.ts
```

Main flow:

```text
User opens /research
  -> enters niche and positioning
  -> ReviewsTable calls /api/research-reviews
  -> OpenAI returns normalized review rows
  -> ReviewsTable calls /api/research-competitors
  -> OpenAI returns competitor rows
  -> PatternAnalyzer summarizes common pains, fears, promises, funnels, and differentiators
```

External systems:

```text
OpenAI Responses API
```

### Lead Generator

Purpose:

```text
Separate Python backend for Instagram lead hunting.
```

Main folder:

```text
backend_lead_hunter/
```

Main files:

```text
backend_lead_hunter/main.py
backend_lead_hunter/config.py
backend_lead_hunter/schemas.py
backend_lead_hunter/services/apify_client.py
backend_lead_hunter/services/competitor_service.py
backend_lead_hunter/services/scraper_service.py
backend_lead_hunter/services/gpt_service.py
backend_lead_hunter/services/storage_service.py
backend_lead_hunter/services/tg_service.py
```

Main stack:

```text
FastAPI
Uvicorn
httpx
OpenAI Python SDK
pydantic-settings
python-dotenv
aiogram
SQLite
```

Public endpoints:

```text
GET  /
POST /hunt-leads
GET  /hunt-leads/{job_id}
```

Main flow:

```text
POST /hunt-leads
  -> create background job
  -> find competitor donor accounts
  -> scrape target posts and comments via Apify
  -> analyze post/comment/profile with GPTService
  -> deduplicate processed posts, comments, and leads in SQLite
  -> send hot lead to Telegram
  -> expose job state through GET /hunt-leads/{job_id}
```

External systems:

```text
Apify
OpenAI
Telegram
SQLite local database
```

## Data Layer

### Supabase

Supabase SQL migrations live in:

```text
supabase/sql/
```

Current migration files:

```text
001_neiroclozer_v0_1.sql
002_expert_memory.sql
003_leads_enrichment.sql
004_gift_followup_tracking.sql
005_messages_message_type_expand.sql
```

Used mainly by:

```text
Neurocloser
Telegram webhook
Gift tracking
Follow-up cron
```

### SQLite

The Lead Generator backend uses a local SQLite database:

```text
backend_lead_hunter/lead_hunter.db
```

This file is ignored by `backend_lead_hunter/.gitignore`.

## Environment Variables

The project uses environment variables for external integrations.

Next.js side examples:

```text
OPENAI_API_KEY
ANTHROPIC_API_KEY
TELEGRAM_BOT_TOKEN
TELEGRAM_WEBHOOK_SECRET
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
CRON_SECRET
PUBLIC_BASE_URL
NEXT_PUBLIC_SITE_URL
CALENDAR_URL
```

Lead Generator side:

```text
backend_lead_hunter/.env
backend_lead_hunter/.env.example
```

## Deployment Shape

Current deployment shape is mixed:

```text
Next.js app           Main web app and Next.js API routes
Python FastAPI app    Separate Lead Generator backend
Supabase              Remote database for Neurocloser
SQLite                Local persistence for Lead Generator deduplication/job data
```

## Boundaries

Recommended boundaries for future work:

```text
Neurocloser changes     Stay in app/api/telegram, app/api/gift, app/api/cron, lib/neiroclozer, lib/supabase-rest, lib/telegram
Research AI changes     Stay in app/research, components/research, app/api/research-*
Lead Generator changes  Stay in backend_lead_hunter
Shared changes          Use only when the task explicitly affects multiple areas
```

## Known Architecture Notes

- This is currently a single repository, not separate repositories per application.
- The frontend and Next.js API routes are in the same Next.js app.
- Lead Generator is already separated physically as a Python backend folder.
- Research AI is separated by route and components, but still lives inside the same Next.js app.
- Neurocloser is mostly API/library driven and does not currently have a dedicated UI folder.
- Runtime logs, `.env`, virtualenv folders, cache folders, and local databases should stay out of git.
