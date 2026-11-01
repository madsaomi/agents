# 📋 Бэклог Проекта (BACKLOG.md)

Список будущих задач, улучшений, фич и технических долгов для проекта **Second Brain Template**.

> [!TIP]
> Когда задача берется в работу, перенеси её описание в `agents/tasks/active_task.md` и создай план (Plan-First).

---

## 🚀 Предстоящие задачи (Upcoming Tasks)

### 📌 Высокий приоритет (High)
- [ ] **TASK-010:** PyPI v0.5.0 — релиз пакета `second-brain-template` по release-checklist (нужен PyPI-токен заказчика, наружное действие). Разблокировано: фабрики root-aware (PLAN-011).
- [ ] Живой смоук Codex `/hooks` (trust-review) — внешний блокер: CLI Codex не установлен у заказчика.

### 📌 Средний приоритет (Medium)
- [ ] **TASK-015:** Root-aware остатки класса BUG-002: `run_integrity_check` (секреты/структура сканируют расположение модуля) и цель `brain dump` (`context_dump.md` пишется рядом с модулем, а не в root).
- [ ] **TASK-011:** `brain graph` — mermaid-визуализация вики-связей `[[...]]` поверх `links.py`.
- [ ] **TASK-012:** `brain digest` — сжатая сводка памяти для веб-чатов (сначала сверить с `dump --budget`, чтобы не дублировать).
- [ ] README на английском (фаза M2 — расширение аудитории).

### 💡 Идеи на будущее (Ideas & Nice-to-Have)
- [ ] Dockerfile и `docker-compose.yml` для изолированного запуска шаблона.
- [ ] Инкрементальная FTS-переиндексация (сейчас пересборка всего индекса).
- [ ] `brain doctor`: проверка установленных pre-commit хуков и `.preset_lock.json`.

---

## ✅ Выполнено (кратко, детали в `agents/history/` и `agents/tasks/archive/`)
- TASK-006 — Кросстулумность Codex/OpenCode (PLAN-006)
- TASK-007 — MCP-инструменты связей/локов/статистики (PLAN-007)
- TASK-008 — `brain doctor`: диагностика окружения (PLAN-008)
- TASK-009 — Надёжность ядра CLI: смок-тесты, декомпозиция, BUG-002 (PLAN-009)
- TASK-014 — Жизненный цикл памяти: handoff/archive/lint (PLAN-010)
- TASK-013 — Root-aware фабрики артефактов (PLAN-011)
