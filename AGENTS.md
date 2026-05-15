<!-- BEGIN:nextjs-agent-rules -->
# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.
<!-- END:nextjs-agent-rules -->

## Git Branch Workflow

Before starting any code or documentation task:

1. Identify the project area for the task:

```text
neurocloser
research-ai
leadgen
shared
infra
docs
```

2. Tell the user which area the task belongs to.
3. Give the exact Git Bash commands to create the branch for the current task.
4. Do not start editing files until the user has created or confirmed the correct branch.

Branch command template:

```bash
git checkout main
git pull
git checkout -b <area>/<task-name>
```

Examples:

```bash
git checkout -b neurocloser/improve-first-reply
git checkout -b research-ai/fix-reviews-table
git checkout -b leadgen/add-source-filter
git checkout -b docs/update-readme
```

Use `main` only as the stable base. Feature and documentation work should happen in task branches.

# Правила проекта

# AI Launch System-это учебно-боевой Next.js-проект, который я собираю в формате AI-first.
Цель проекта — поэтапно собрать внутреннюю систему запуска.

## Общий принцип
Работаем только маленькими шагами.
Не делаем большие рефакторинги без запроса.
Не меняем лишние файлы.

## Как агент должен отвечать
Сначала дай короткий план.
Потом перечисли файлы, которые собираешься менять.
Потом покажи код.
Потом дай шаги ручной проверки.
Потом кратко объясни, что было сделано и зачем.

## Ограничения
- не ломай существующую структуру проекта
- не трогай package.json без необходимости
- не добавляй новые библиотеки без явного запроса
- не меняй несколько частей проекта сразу
- не делай "улучшения от себя", если они не были запрошены

## Формат работы
Одна задача = один маленький шаг.
Сначала делаем локально и просто.
Потом проверяем руками.
Потом только следующий шаг.

## Что считать успехом
Изменение видно в браузере.
Нет ошибок в терминале.
Я понимаю, что именно поменялось.
