# Current Architecture

This document describes the current project structure.

## Repository Model

The project is one git repository with several product areas inside it:

```text
ai-launch-system-app/
  app/
  components/
  public/
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
public/       Static assets
```

Important entry points:

```text
app/layout.tsx          Root layout
app/page.tsx            Home page
app/research/page.tsx   Research AI page
app/test/page.tsx       Test page
```

### 2. Next.js API Routes

API routes live inside `app/api/`.

```text
app/api/research-reviews/route.ts
app/api/research-competitors/route.ts
```

Current responsibilities:

```text
research-reviews       Generates market/review research via OpenAI
research-competitors   Generates competitor analysis via OpenAI
```

## Product Areas

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
Separate Python backend for lead hunting.
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
OPENAI_MODEL
OPENAI_RESEARCH_MODEL
```

Lead Generator side:

```text
backend_lead_hunter/.env
backend_lead_hunter/.env.example
```

## Deployment Shape

Current deployment shape:

```text
Next.js app           Main web app and Research AI API routes
Python FastAPI app    Separate Lead Generator backend
SQLite                Local persistence for Lead Generator deduplication/job data
```

## Boundaries

Recommended boundaries for future work:

```text
Research AI changes     Stay in app/research, components/research, app/api/research-*
Lead Generator changes  Stay in backend_lead_hunter
Shared changes          Use only when the task explicitly affects multiple areas
```

## Known Architecture Notes

- This is currently a single repository for Launch OS modules.
- The frontend and Research AI API routes are in the same Next.js app.
- Lead Generator is separated physically as a Python backend folder.
- Research AI is separated by route and components, but still lives inside the same Next.js app.
- Runtime logs, `.env`, virtualenv folders, cache folders, and local databases should stay out of git.
