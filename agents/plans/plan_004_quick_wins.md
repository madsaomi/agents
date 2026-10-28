# 📐 План реализации: PLAN-004 — Быстрые победы: секрет-сканер, brain stats, GitHub-аннотации, tour

> **Статус:** ✅ COMPLETED (все 4 этапа выполнены, 146 тестов)  
> **Дата создания:** 2026-10-28  
> **Автор / Агент:** MiMo (OpenCode)  
> **Связанная задача:** [TASK-004](../tasks/active_task.md)  
> **Целевая ветка / Ревизия:** main  

---

## 1. 🎯 Цель и контекст

- **Проблема / Задача:** После PLAN-003 шаблон функционален, но у него четыре недоработки «малой кровью»: (1) секреты проверяются только в `.mcp.json` — в остальных файлах дыра; (2) нет одной команды, показывающей здоровье памяти; (3) WARN от `check_integrity` в CI видны только в логе, а не в PR; (4) новый пользователь не понимает, с чего начать — шаблон красивый, но непонятный.
- **Ожидаемый результат:** `check_integrity` ловит секреты в любом файле (и до коммита через pre-commit), `brain.py stats` даёт дашборд памяти одной командой, CI показывает ошибки как GitHub-аннотации прямо в PR, `brain.py tour` проводит нового пользователя по всем возможностям за 2 минуты.

---

## 2. 🔍 Анализ и затронутые компоненты

### Затронутые файлы:
- `[NEW]` `agents/tools/secret_scan.py` — stdlib-сканер секретов: регексы токенов (OpenAI, Anthropic, GitHub, Slack, AWS, приватные ключи, generic `password=`/`api_key=`), allowlist-плейсхолдеры (`${ENV}`, `your_token`, `.env.example`, `tests/`), API `scan_files(paths)` / `scan_project(root)`.
- `[NEW]` `agents/tools/stats.py` — дашборд памяти: счётчики по разделам, открытые пункты чек-листов, битые относительные ссылки, устаревшие записи, активные локи, размер FTS-индекса; вывод — таблица + `--json`.
- `[MODIFY]` `agents/tools/check_integrity.py` — секция 11 «Секреты в файлах» (ошибка, exit 1); поддержка GitHub Actions-аннотаций (`::error`/`::warning`, авто-детект `GITHUB_ACTIONS`).
- `[MODIFY]` `agents/tools/brain.py` — подкоманды `stats` и `tour`.
- `[MODIFY]` `README.md`, `agents/architecture/CODEBASE_MAP.md`, `agents/STATUS.md` — документация новых команд.
- `[NEW]` `tests/test_secret_scan.py`, `tests/test_stats.py` — модульные тесты.
- `[DELETE]` — нет.

### Зависимости и влияние:
- Новые библиотеки: НЕТ (только stdlib: `re`, `json`, `argparse`, `pathlib`).
- Влияние на API: только новые подкоманды CLI; `check_integrity` добавляет одну секцию — существующие вызывающие (CI, git-хук) не меняются.
- Риск Breaking changes: НЕТ.
- Pre-commit хук (`install_hooks.py`) уже запускает `check_integrity.py` — секрет-сканер включается в него автоматически, без правки хука.

---

## 3. 📝 Пошаговый план реализации (Atomic Steps)

- [x] **Этап 1: Секрет-сканер**
  - [x] 1.1: `secret_scan.py` — паттерны токенов + маскировка плейсхолдеров (`${VAR}`, `your_…`, `xxx`, `<…>`, `example`, `changeme`); `scan_files()` возвращает список `{file, line, kind}`.
  - [x] 1.2: `scan_project(root)` — обход git-трекаемых файлов (fallback — дерево, исключая `.git`, `__pycache__`, `.brain_index.db`); skip-list: `.env.example`, `tests/`, файлы с маркером `# secretscan: off`.
  - [x] 1.3: Секция 11 в `check_integrity` (ошибка при находке); авто-запуск в pre-commit через уже существующий вызов.
- [x] **Этап 2: `brain.py stats`**
  - [x] 2.1: `stats.py` — счётчики разделов памяти (plans/tasks/history/bugs/decisions/walkthroughs), открытые `[ ]`-пункты в активной задаче и активных планах, битые относительные markdown-ссылки, записи старше 90 дней, локи `claim`, размер FTS-индекса.
  - [x] 2.2: Подкоманда `stats` в `brain.py` (таблица + `--json` для машинного чтения).
- [x] **Этап 3: GitHub-аннотации + tour**
  - [x] 3.1: `log_check` умеет `file=`; при `GITHUB_ACTIONS=true` каждый FAIL/WARN дублируется как `::error file=…::…` / `::warning file=…::…` (файл известен — по пути проверки, иначе корень).
  - [x] 3.2: `brain.py tour` — пошаговый гайд (Enter → следующий экран): память → Plan-First → sync → хуки → поиск → claim/dump → MCP → пресеты; флаг `--list` для неинтерактивного вывода.
- [x] **Этап 4: Тестирование, документирование и сдача**
  - [x] 4.1: `tests/test_secret_scan.py` (находка, плейсхолдеры не считаются, allowlist, `# secretscan: off`), `tests/test_stats.py` (счётчики, битые ссылки, `--json`), смоук `tour --list`.
  - [x] 4.2: README (разделы «Безопасность» и «Тур»), `CODEBASE_MAP.md`, `STATUS.md`; прогон 100%+; фиксация сессии в `agents/history/`.

---

## 4. 🛡️ Риски, сайд-эффекты и план отката

- **Ложные срабатывания сканера** блокируют коммиты → мягкие паттерны только для generic-ключей, маска плейсхолдеров, skip-list, маркер `# secretscan: off`; ложные — WARN? Нет: реальный секрет — ошибка (это и есть цель), но маски должны покрывать типичные шаблоны (`${ENV}` — канон проекта).
- **Скорость скана в pre-commit** → обход только git-трекаемых файлов (в шаблоне их ~200).
- **Аннотации GitHub** не поддержаны локально → вывод только при `GITHUB_ACTIONS=true`, обычный вывод не меняется.
- **Откат:** `git revert` коммита этапа; новые файлы не трогают существующие контракты.

---

## 5. 🧪 План тестирования и критерии приемки

1. Автотесты: `python -m unittest discover -s tests` — ≥ 117 + новые, 0 падений.
2. Ручная проверка:
   - `python brain.py check` — секция 11 зелёная; временный файл с `sk-proj-…` → FAIL и отказ коммита.
   - `python brain.py stats` и `stats --json` — корректные счётчики, битые ссылки ловятся.
   - `GITHUB_ACTIONS=true python brain.py check` — появляются строки `::warning file=…`.
   - `python brain.py tour --list` — все 8 экранов гайда.
3. Definition of Done:
   - [x] Код компилируется (`python -m compileall`), только stdlib.
   - [x] Тесты зелёные, `check_integrity` — 0 ошибок / 0 WARN, `sync --check` чист.
   - [x] Чек-лист плана `[x]`, README/CODEBASE_MAP обновлены.
