# 📋 Активная задача: TASK-010 — PyPI v0.5.0 (подготовка завершена)

**Статус:** 🔵 IN_PROGRESS — остался шаг публикации (нужен PyPI-токен заказчика)  
**Дата создания:** 2026-11-01  
**Исполнитель:** ZCode (GLM)  
**Приоритет:** HIGH  
**Связанный план:** [`PLAN-014`](../plans/plan_014_pypi_v050_podgotovka_reliza.md)  

---

## Чек-лист

### Предыдущий план — [PLAN-013](../plans/plan_013_finalnyy_kod_root-check_dump-target_digest.md): ✅ COMPLETED
- [x] `run_integrity_check(fix=, root=)` — проверяет проект пользователя (класс BUG-002 закрыт полностью)
- [x] `brain dump` пишет `context_dump.md` в `root/agents/tools/`
- [x] `brain digest [--tokens N] [--copy]` — дайджест поверх handoff/stats (PLAN-013)
- [x] 305 тестов, sync --check чист, integrity 100%, коммит

### PLAN-014 — PyPI v0.5.0
- [x] Шаг 1: release-checklist пройден (тесты 305, integrity 100%, sync чист, секрет-скан чист)
- [x] Шаг 2: версия 0.4.0 → **0.5.0**; установлены build/twine
- [x] Шаг 3: `python -m build` — sdist + wheel собраны; `twine check` — PASSED
- [x] Шаг 4: venv-смоук дистрибутива из чужого cwd: `brain --help`/`status`/`plan` пишут в cwd-проект (root-aware работает в установленном пакете)
- [x] Шаг 5: коммит `chore(release): v0.5.0`, тег `v0.5.0`
- [ ] **Шаг 6: публикация** — `twine upload dist/*` (нужен PyPI-токен заказчика; наружное действие)

## Инструкция по публикации (шаг 6)

```bash
# 1. Создай API-токен на pypi.org (Account settings → API tokens, scope: entire account или новый проект)
# 2. Загрузи (токен передаётся один раз, не коммитить!):
python -m twine upload dist/* -u __token__ -p <PYPI_TOKEN>
# 3. Проверь: https://pypi.org/project/second-brain-template/
# 4. После публикации: pip install second-brain-template
```
