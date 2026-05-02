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

Система перестала быть “сборщиком данных” и стала инструментом принятия решений.

