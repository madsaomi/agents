---
name: nextjs-page
description: Пошаговое добавление новой страницы/фичи в Next.js App Router: маршрут → серверный компонент → данные → мутации → тесты.
---

# 📄 Новая страница (Next.js App Router)

## Порядок (Plan-First: сначала план в `agents/plans/`)
1. **Маршрут** `app/<route>/page.tsx` (серверный компонент по умолчанию):
   ```tsx
   export default async function Page({ searchParams }: { searchParams: Promise<{ q?: string }> }) {
     const { q } = await searchParams;
     const items = await getItems(q);
     return <ItemList items={items} />;
   }
   ```
2. **Данные:** `lib/`-функции с `fetch(..., { next: { revalidate } })` или запрос в БД напрямую; несколько источников — параллельно.
3. **Состояния:** `loading.tsx` (спиннер/Skeleton), `error.tsx` (с кнопкой retry) в сегменте.
4. **Мутации** — server action `lib/actions/<feature>.ts`:
   - zod-валидация входа;
   - проверка сессии/прав на сервере;
   - `revalidatePath` после успеха.
5. **Интерактивные куски** — отдельные client-компоненты (`"use client"`), страница остаётся серверной.
6. **Тесты:** Vitest на утилиты/actions, Playwright на критичный путь страницы.

## Чек-лист
- [ ] `"use client"` только там, где действительно нужен.
- [ ] Секреты не в клиентском бандле (проверь `NEXT_PUBLIC_`).
- [ ] Страница имеет loading/error состояния.
- [ ] `pnpm lint && pnpm test` — зелёные.
- [ ] `agents/architecture/CODEBASE_MAP.md` обновлён.
