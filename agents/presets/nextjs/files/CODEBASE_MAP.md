# 🗺️ Карта кодовой базы: Next.js (пресет nextjs)

```
.
├── app/                           # 🛣️ App Router
│   ├── (auth)/                    # Группа маршрутов с авторизацией
│   │   ├── login/page.tsx
│   │   └── layout.tsx
│   ├── (main)/<route>/page.tsx    # Основные страницы
│   ├── api/                       # Route handlers (если не server-only)
│   ├── loading.tsx / error.tsx    # Состояния загрузки/ошибки
│   └── layout.tsx                 # Корневой layout
├── components/                    # Переиспользуемые UI-компоненты
│   └── ui/                        # Примитивы (кнопки, инпуты)
├── lib/                           # 💼 Утилиты и бизнес-логика
│   ├── actions/                   # Server Actions (мутации)
│   ├── db.ts / auth.ts            # Клиенты БД/аутентификации
│   └── validations/               # Zod-схемы
├── hooks/                         # Кастомные React-хуки
├── tests/                         # Vitest + Playwright
├── .env.example
└── agents/                        # 🧠 Second Brain
```

## Карта страниц (заполни после генерации)
| Маршрут | Страница | Данные | Мутации |
|---|---|---|---|
| `/login` | `(auth)/login/page.tsx` | — | `actions/auth.ts` |
