# Project Areas

This file defines how we split work inside one git repository. A git branch always belongs to the whole repository, but each task should stay inside one project area.

## Applications

### Neurocloser

Branch prefix:

```bash
neurocloser/<task-name>
```

Main files and folders:

```text
lib/neiroclozer/
app/api/telegram/
app/api/cron/gift-followups/
app/api/gift/
components/ReviewsTable.tsx
```

### Research AI

Branch prefix:

```bash
research-ai/<task-name>
```

Main files and folders:

```text
app/research/
components/research/
app/api/research-competitors/
app/api/research-reviews/
```

### Lead Generator

Branch prefix:

```bash
leadgen/<task-name>
```

Main files and folders:

```text
backend_lead_hunter/
```

## Shared Areas

These areas are shared. Change them only when the task explicitly needs shared project code.

```text
app/layout.tsx
app/page.tsx
app/globals.css
components/
lib/
supabase/
next.config.ts
tsconfig.json
vercel.json
```

## Branch Rules

1. One task = one branch.
2. Name the branch by project area:

```bash
neurocloser/<task-name>
research-ai/<task-name>
leadgen/<task-name>
shared/<task-name>
infra/<task-name>
docs/<task-name>
```

3. Do not mix different applications in one branch.
4. If a task needs shared code, use `shared/<task-name>` or clearly state which applications are affected.
5. Check status before starting:

```bash
git status
```

6. Create a new branch from `main`:

```bash
git checkout main
git pull
git checkout -b leadgen/example-task
```

7. Push only the current branch:

```bash
git push -u origin leadgen/example-task
```

## Current Notes

- `backend_lead_hunter/.gitignore` already ignores `.server.*.log`, `.uvicorn.*.log`, `.env`, `.venv/`, and database files.
- If these files were already tracked by git, remove them from the git index separately with `git rm --cached` while keeping local files.
