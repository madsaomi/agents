# 🤖 AI Agent System Entrypoint (AGENTS.md)

> [!IMPORTANT]
> **ВНИМАНИЕ ДЛЯ ЛЮБОГО AI-АГЕНТА (Antigravity, Claude, ChatGPT, Cursor, Windsurf, Aider):**  
> Этот проект использует стандартизированную систему долговременной памяти и управления разработкой **«Второй Мозг» (Second Brain)** в каталоге [`agents/`](file:///agents/).  
> Любые изменения в проекте **СТРОГО** регламентируются документацией из этой папки.

---

## 🚀 Протокол входа агента в проект

### Шаг 1: Обязательное чтение перед любым действием
1. Открой и изучи главный навигатор: 👉 **[`agents/AGENT_GUIDE.md`](file:///agents/AGENT_GUIDE.md)**
2. Ознакомься со строгими запретами: 👉 **[`agents/rules/ANTI_PATTERNS.md`](file:///agents/rules/ANTI_PATTERNS.md)**
3. Ознакомься с регламентом работы: 👉 **[`agents/rules/AGENT_RULES.md`](file:///agents/rules/AGENT_RULES.md)**

### Шаг 2: Проверка инициализации проекта
- Если этот проект только что создан (или папка `agents/` скопирована в новый репозиторий, и там стоят шаблоны-заглушки):
  👉 Запусти или следуй протоколу: **[`agents/rules/ONBOARDING_PROTOCOL.md`](file:///agents/rules/ONBOARDING_PROTOCOL.md)**  
  (Или выполни утилиту: `python agents/tools/init_project.py`)

### Шаг 3: Текущий контекст и задачи
- Текущий статус проекта: 👉 **[`agents/STATUS.md`](file:///agents/STATUS.md)**
- Активная задача с чек-листом: 👉 **[`agents/tasks/active_task.md`](file:///agents/tasks/active_task.md)**
- Карта кодовой базы: 👉 **[`agents/architecture/CODEBASE_MAP.md`](file:///agents/architecture/CODEBASE_MAP.md)**
- Известные баги и решения: 👉 **[`agents/bugs_and_fixes/`](file:///agents/bugs_and_fixes/)**

---

## ⚡ Главные правила взаимодействия:
1. **Никаких изменений вслепую:** Сначала читай код, архитектуру и известные баги, затем изменяй.
2. **Параллельная фиксация задач:** Выполняешь задачу — отмечай прогресс в `agents/tasks/active_task.md`.
3. **Фиксация багов:** Столкнулся с ошибкой или сбоем сборки/тестов — опиши её в `agents/bugs_and_fixes/` по шаблону.
4. **Непрерывность истории:** В конце сессии создай новый отчет в `agents/history/` (старые файлы никогда не затирать!).
