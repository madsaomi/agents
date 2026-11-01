# 🧠 AI-Ready Project Template ("Second Brain" for Agents)

[![CI Status](https://img.shields.io/badge/CI-Passing-brightgreen)](.github/workflows/integrity.yml)
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![AI Agents](https://img.shields.io/badge/AI%20Agents-Antigravity%20|%20Cursor%20|%20Claude%20|%20Windsurf%20|%20Copilot-blueviolet)](AGENTS.md)

Универсальный шаблон долгосрочной памяти, требований к продукту, архитектуры и регламентов разработки для любых AI-агентов (Google Antigravity, Cursor, Claude Code, ChatGPT, Windsurf, GitHub Copilot, Aider и др.).

---

## ⚡ Быстрый старт с единым CLI (`brain.py`)

Управляйте проектом одной командой прямо из корня репозитория:
```bash
python brain.py status              # 📊 Терминальный дашборд проекта и прогресс задач
python brain.py plan "Feature Name" # 📐 Создать план реализации (Plan-First)
python brain.py bug "Error Title"   # 🐛 Зафиксировать ошибку в базе знаний
python brain.py adr "Choice Title"  # 🏛️ Зафиксировать архитектурное решение (ADR)
python brain.py check               # 🧠 Проверить целостность Второго Мозга (--fix для автопочинки)
python brain.py doctor [--json]     # 🩺 Диагностика окружения (Python, FTS5, git, индекс, буфер, [mcp])
python brain.py stats [--json]      # 📊 Дашборд здоровья памяти (битые ссылки, устаревшее, локи)
python brain.py tour [--list]       # 🧭 Интерактивный гид для нового пользователя
python brain.py sync [--check]      # ⚙️ Сгенерировать конфиги AI-инструментов из agents/rules/CORE_RULES.md
python brain.py search "jwt"        # 🔍 Полнотекстовый поиск по памяти (SQLite FTS5, --reindex, --tag, --since)
python brain.py links BUG-001       # 🔗 Вики-связи [[...]]: исходящие, обратные ссылки, --unresolved
python brain.py graph [--max N]     # 🕸️ Mermaid-граф вики-связей (узлы-записи, битые — пунктиром)
python brain.py handoff [--copy]    # 🤝 Эстафета для следующего агента (статус, задача, план, баги, история)
python brain.py archive [--force]   # 🗄️ Архивировать завершённую задачу и сбросить active_task
python brain.py claim TASK-003      # 🔒 Забрать задачу (параллельным агентам — сюда не лезть)
python brain.py release TASK-003    # 🔓 Освободить задачу
python brain.py presets             # 🧩 Показать пресеты стека (django-drf, aiogram-bot, fastapi, nextjs)
python brain.py preset <имя>        # 🧩 Применить пресет стека к проекту
python brain.py upgrade             # ⬆️ Обновить шаблоны, не затирая свои правки и историю
python brain.py dump [--budget N]   # 📦 Полный контекст в буфер для веб-чатов (N — лимит токенов)
python brain.py digest [--tokens N] # 🧠 Компактный дайджест проекта для веб-чатов (--copy — в буфер)
python brain.py end                 # 🏁 Завершить сессию и сохранить историю
```

> 🧭 **Новичок?** Начни с `python brain.py tour` — интерактивный гайд по всем командам и разделам памяти за 2 минуты.

---

## 🚀 Как использовать в любом новом проекте (За 3 простых шага):

### Шаг 1: Скопируй в новый проект
Когда ты создаешь любой новый проект (веб-сайт, Telegram-бот, мобильное приложение, Python-скрипт, микросервис):
Скопируй в корень нового проекта:
1. Папку **`agents/`**
2. Файлы конфигурации AI: **`AGENTS.md`**, **`brain.py`**, **`.cursorrules`**, **`.cursor/`**, **`CLAUDE.md`**, **`.windsurfrules`**, **`.env.example`**

### Шаг 2: Инициализация (2 варианта)

**Вариант А (Автоматический через AI):**
Просто напиши своему AI-ассистенту:
> *"Я скопировал папку `agents/`. Инициализируй Второй Мозг проекта согласно `AGENTS.md` и `agents/rules/ONBOARDING_PROTOCOL.md`."*

**Вариант Б (Через скрипт в одну команду):**
```bash
python agents/tools/init_project.py --name "Мой Проект" --desc "Краткое описание" --stack "FastAPI + React"
```
*(Или запусти без параметров `python agents/tools/init_project.py` для интерактивного ввода).*

**Пресеты стека (django-drf, aiogram-bot, fastapi, nextjs):**
```bash
python brain.py presets                    # что доступно
python brain.py init --preset django-drf   # инициализация + пресет одной командой
# или поверх существующего проекта:
python brain.py preset aiogram-bot
```
Пресет подставляет `CODING_STANDARDS`, `CODEBASE_MAP`, QA-чек-лист, `.env.example`, Docker/CI и стековых субагентов/скиллов (например, django-drf даёт `django-migration-reviewer`, `drf-api-designer` и скиллы `new-drf-endpoint`, `celery-task`, `db-migration`). Свои правки установленных файлов не затираются — сравнение по хешам в `agents/.preset_lock.json`.

### Шаг 3: Включение защиты коммитов (Git Hook)
```bash
python agents/tools/install_hooks.py
```
*Установит pre-commit хук, который не позволит закоммитить сломанную структуру или код без плана.*

### Шаг 4: Работа в удовольствие!
Теперь любой агент или модель (Gemini, Claude 3.7, GPT-4o, DeepSeek):
- Всегда знает цель продукта и требования благодаря `agents/product/PRD.md`.
- Не теряет контекст при перезапуске сессий.
- Мгновенно подхватывается в Google Antigravity (`.agents/skills/`), Cursor (`.cursorrules`, `.cursor/rules/`), Claude Code (`CLAUDE.md`), Windsurf (`.windsurfrules`) и Copilot (`copilot-instructions.md`).
- Не наступает повторно на известные баги (все фиксируются в `agents/bugs_and_fixes/`).
- Ведет непрерывную историю в `agents/history/`.

---

## 🛠️ Встроенные утилиты автоматизации (Python Standard Library)

Все скрипты не требуют установки сторонних библиотек и работают прямо из коробки:

1. **Проверка целостности Второго Мозга:**
   ```bash
   python agents/tools/check_integrity.py
   # С автоисправлением недостающих папок:
   python agents/tools/check_integrity.py --fix
   ```
   Проверяет наличие всех каталогов, файлов, шаблонов, конфигов AI и корректность структуры.

2. **Быстрая инициализация нового проекта:**
   ```bash
   python agents/tools/init_project.py --name "ProjectName" --desc "Description" --stack "TechStack"
   ```
   Автоматически заменяет все плейсхолдеры в файлах за 1 секунду, не затрагивая чистые шаблоны.

3. **Мгновенное создание плана (Plan-First):**
   ```bash
   python agents/tools/new_plan.py --name "Auth System" --task "TASK-002"
   ```
   Автоматически вычисляет следующий номер плана (`plan_001_...`), подставляет метаданные и генерирует бланк.

4. **Сборка контекста для веб-чатов (ChatGPT, Claude Web):**
   ```bash
   python agents/tools/dump_context.py
   ```
   Упаковывает текущий статус, активный план, задачи, архитектуру и последнюю сессию, и **автоматически копирует в буфер обмена**! Просто вставьте (`Ctrl+V`) в любой браузерный чат.

5. **Быстрое завершение сессии:**
   ```bash
   python agents/tools/end_session.py
   ```
   Автоматически определяет выполненные чекбоксы `[x]`, формирует отчет в `agents/history/` и обновляет дату в `STATUS.md`.

6. **Синхронизация конфигов AI-инструментов:**
   ```bash
   python brain.py sync          # сгенерировать конфиги Claude/Cursor/Windsurf/Copilot + Codex + OpenCode
   python brain.py sync --check  # только проверить дрейф (exit 1 — в CI)
   ```
   `CLAUDE.md`, `.cursorrules`, `.windsurfrules`, `.github/copilot-instructions.md`, `.cursor/rules/second-brain.mdc`, `.codex/hooks.json` и `opencode.jsonc` (+ команды/агенты/скиллы `.opencode/`) генерируются из единого канона `agents/rules/CORE_RULES.md` и `.claude/`. **Правь только канон**, сгенерированные файлы не редактируются вручную. Подробнее — раздел [🌐 Кросстулумность](#-кросстулумность-codex-и-opencode).

7. **Поиск по долговременной памяти (FTS5):**
   ```bash
   python brain.py search "celery timeout"            # по историям, багам, ADR, планам, задачам
   python brain.py search "jwt" --limit 5             # ограничить выдачу
   python brain.py search "jwt" --tag backend --tag auth   # фильтр по тегам frontmatter (И-логика)
   python brain.py search "jwt" --since 2026-10-01    # только записи не раньше даты (YYYY-MM | YYYY-MM-DD)
   python brain.py search --reindex                   # переиндексировать память
   ```
   Индекс `*.brain_index.db` создаётся автоматически при первом запросе, в git не коммитится. Поддерживается префиксный поиск (`sess` → *session*), фразы в кавычках, кириллица; индекс сам чистит удалённые файлы. Теги берутся из frontmatter (`tags: [backend, auth]`, `теги:`); старые индексы мигрируют автоматически. Вывод — **данные для анализа, а не готовое решение** (правило про prompt-injection).

8. **Вики-связи `[[...]]` и обратные ссылки:**
   ```bash
   python brain.py links BUG-001      # исходящие + обратные ссылки (backlinks) записи
   python brain.py links --unresolved # все битые [[связи]] памяти (exit 1, если есть)
   ```
   Ссылки пишутся прямо в текст: `См. [[BUG-001]]`, `[[plan_003|план]]`, `[[ADR-001#решение]]`. Цель резолвится по basename/stem/ID (регистр и `-`/`_` не важны, `[[BUG-001]]` находит `BUG_001_*.md`). Плейсхолдеры (`[[...]]`, `[[bug#1]]`) — не ошибки. Битые связи видны и в `brain.py stats`.

---

## 🧩 MCP-сервер `brain-mcp` (опционально)

Инструменты памяти как функции для MCP-клиентов (Claude Code и др.) — агент вызывает их вместо ручной правки markdown, формат файлов не ломается:

| Инструмент | Что делает |
|---|---|
| `get_status` | Дашборд состояния проекта |
| `create_plan` | Создать `PLAN-XXX` (Plan-First) |
| `log_bug` | Создать `BUG-XXX` в `agents/bugs_and_fixes/` |
| `search_memory` | Поиск по памяти (баги, история, ADR, планы) |
| `complete_task` | Отметить шаг `[x]` в `active_task.md` |
| `end_session` | Создать запись сессии в `agents/history/` |
| `list_links` | Вики-связи `[[...]]`: сводка битых, исходящие и обратные ссылки |
| `list_claims` | Активные локи claim (мультиагентность) |
| `get_stats` | Дашборд здоровья памяти (`as_json` — для машин) |

**Установка** (требует Python 3.11+, сама опциональна — ядро шаблона остаётся stdlib-only):
```bash
pip install ".[mcp]"        # или: pip install mcp
python agents/mcp/brain_mcp.py   # запуск сервера (stdio)
```

В `.mcp.json` в корне лежат пресеты подключения: **brain** (этот сервер), **filesystem**, **github**, **postgres** (read-only), **context7** (документация библиотек), **playwright**, **sentry**. Claude Code запросит подтверждение проектных серверов при старте; отключи ненужные через `/mcp`. Секреты задаются только через переменные окружения (`${GITHUB_TOKEN}` и т.п.) — в репозиторий значения не попадают.

---

## 🌐 Кросстулумность: Codex и OpenCode

`brain.py sync` рендерит исполняемые правила для **всех** поддерживаемых инструментов из одного канона (`agents/rules/CORE_RULES.md` + `.claude/`):

| Инструмент | Что генерирует `sync` | Исполняемые правила |
|---|---|---|
| Claude Code / Cursor / Windsurf / Copilot | 5 конфигов (`CLAUDE.md`, `.cursorrules`, …) | `.claude/settings.json` → хуки Python |
| **Codex** | `.codex/hooks.json` + `.agents/skills/*/SKILL.md` (5 скиллов) | Те же 4 хука Python через `$(git rev-parse --show-toplevel)` |
| **OpenCode** | `opencode.jsonc` (7 MCP), `.opencode/commands/` (6), `.opencode/agents/` (7), `.opencode/skills/` (5), `.opencode/plugins/second_brain/index.ts` | Плагин → тот же `pre_tool_gate.py` |

### Codex

- **Правила** — `AGENTS.md` в корне (Codex читает его автоматически). Промпты-команды Codex больше не поддерживают `.codex/prompts/` (deprecated) — используйте скиллы.
- **Скиллы** — зеркалятся в `.agents/skills/<name>/SKILL.md` (канон — `.claude/skills/`).
- **Хуки** — `.codex/hooks.json`: Plan-First-гейт, запрет чтения секретов, линт после правки, журнал сессии. Формат хуков идентичен Claude Code (`permissionDecision: deny`), поэтому переиспользуются те же python-скрипты.
- **⚠️ Первый шаг после `sync`:** Codex требует trust-review хуков — выполни `/hooks` в CLI и подтверди определения, иначе хуки будут пропускаться (защита просто не включится, сессия работает).

### OpenCode

- **Конфиг** — `opencode.jsonc` в корне: `$schema`, `mcp.servers` (те же 7 серверов, что `.mcp.json`; секреты — `{env:VAR}`), запреты правки `*.env`/`*.pem`/`*.key` (`.env.example` разрешён).
- **Команды** — `.opencode/commands/*.md`, вызываются как `/plan`, `/bug` и т.д. Тело шаблона и `$ARGUMENTS` общие с Claude Code, поэтому трансформируются автоматически.
- **Сабагенты** — `.opencode/agents/*.md` (`mode: subagent`); read-only агенты (planner, reviewer, security-auditor) получают `permissions: deny edit/shell`.
- **Скиллы** — `.opencode/skills/*/SKILL.md`, зеркала канона.
- **Плагин** — `.opencode/plugins/second_brain/index.ts` подключает тот же `pre_tool_gate.py` к `permission.evaluate`: правка кода без активного плана и чтение секретов блокируются с причиной из `agents/rules/ANTI_PATTERNS.md`. Ошибка гейта — fail-open (как у Claude-хуков).

Проверка: `opencode plugin list` (second_brain), `opencode mcp list` (7 серверов), `opencode debug agents` (7 сабагентов).

> Всё сгенерированное правится только через `python brain.py sync` — ручная правка = дрейф, который ловит `sync --check` в CI.

---

## 🛡️ Безопасность: сканер секретов

`brain.py check` (а значит и git pre-commit, и CI) дополнительно сканирует **все tracked и untracked файлы** на предмет утечек: токены OpenAI/Anthropic/GitHub/Slack/AWS/Stripe, приватные ключи, `password=`/`api_key=`. 

```bash
python agents/tools/secret_scan.py   # только сканер, exit 1 — если найдено
```

- **Плейсхолдеры не считаются секретами:** `${ENV}`, `{VAR}`, `your_...`, `changeme`, значения из `os.environ` — канон проекта (секреты только через `${ENV}`) не блокирует коммиты.
- **Allowlist:** `.env.example`, каталоги `tests/`; точечное отключение файла — маркер `secretscan: off` в любом месте файла.
- В **GitHub Actions** каждый FAIL/WARN дублируется аннотацией `::error file=…` / `::warning file=…` — проблемы видны прямо в PR, а не в логе.

---

## 🤝 Параллельная работа агентов (`claim` / `release`)

Несколько сессий/агентов работают над одним проектом без конфликтов — задача «забирается» локом:

```bash
python brain.py claim TASK-003 --note "пишу парсер"   # 🔒 забрать задачу
python brain.py claim TASK-003                         # повторно = обновить heartbeat (удержание)
python brain.py claims                                 # список активных блокировок
python brain.py release TASK-003                       # 🔓 освободить
```

- **Атомарность:** лок создаётся через `O_CREAT|O_EXCL` — из параллельных claim выигрывает ровно один.
- **Отказ по-человечески:** второй агент видит имя владельца, PID и подсказку `--force`.
- **Протухание:** активность держится на heartbeat (повторный claim) с TTL 45 минут (`BRAIN_LOCK_TTL_MINUTES`); процесс команды `claim` завершается сразу, поэтому живость определяется не PID, а свежестью heartbeat. Протухший лок перехватывается без `--force`.
- **Git worktree** для изоляции: `python brain.py claim TASK-003 --worktree` создаёт `worktree` + ветку `task/task-003`; `release TASK-003 --worktree` удаляет worktree (только если он чистый, иначе — явный `--force`).
- Локи лежат в `agents/tasks/.locks/` (в `.gitignore` — локальное состояние, в репозиторий не попадает).

**Сжатие контекста под лимит:** `python brain.py dump --budget 4000` — при превышении секции сначала автосуммируются (остаются заголовки/чек-листы/таблицы), затем отбрасываются низкоприоритетные (глоссарий → правила → PRD → …), ядро «статус + активная задача» удерживается до крайнего случая. Оценка токенов грубая (~3 символа/токен для смешанного ru/en markdown).

---

## ⬆️ Обновление шаблона (`brain upgrade`)

```bash
python brain.py upgrade
```

Обновляет шаблонные файлы до актуальных версий **без затирания твоих данных**:
- Сгенерированные конфиги пересинхронизируются из `agents/rules/CORE_RULES.md` (`sync`).
- Файлы из пресетов обновляются только если ты их не менял (проверка sha256 в `agents/.preset_lock.json`); свои правки сохраняются — upgrade перечисляет их и предлагает сверить вручную.
- **Никогда не трогает** `agents/history/`, `agents/plans/`, `agents/tasks/`, `agents/bugs_and_fixes/` и другие твои артефакты.
- Завершается запуском `check_integrity.py --fix` (восстановление недостающих каталогов).

## 📦 Установка CLI как пакета (опционально)

Ядро шаблона работает без установки (`python brain.py ...` из корня). Для глобальной команды `brain`:

```bash
pip install .            # или: pipx install .
brain status             # команда работает в каталоге любого проекта с agents/
pip install ".[mcp]"     # + MCP-сервер brain-mcp (Python 3.11+)
```

Пакет включает шаблоны и пресеты (`agents/rules`, `agents/templates`, `agents/presets`) — `brain preset django-drf` работает и из установленного пакета. Требуется Python 3.9+ (MCP-extra — 3.11+).

---

## 🗺️ Полная структура «Второго Мозга» (`agents/`)

```
agents/
├── AGENT_GUIDE.md                 # 🌟 Главный навигатор по «Второму Мозгу»
├── STATUS.md                      # 📊 Дашборд состояния проекта и прогресса
├── GLOSSARY.md                    # 📖 Глоссарий терминов предметной области
│
├── product/                       # 🎯 Продуктовые требования и развитие
│   ├── PRD.md                     # Product Requirements Document
│   └── ROADMAP.md                 # Продуктовый план (Now / Next / Later)
│
├── rules/                         # 📜 Обязательные правила для агентов
│   ├── AGENT_RULES.md             # Регламент сессии и передачи эстафеты
│   ├── ANTI_PATTERNS.md           # Строгие запреты (секреты, затирание истории)
│   ├── CODING_STANDARDS.md        # Стандарты архитектуры и чистоты кода
│   └── ONBOARDING_PROTOCOL.md     # Протокол авто-инициализации в новом проекте
│
├── templates/                     # 📐 Бланки документов (заполнять только их!)
│   ├── template_plan.md           # Бланк плана реализации (Plan-First)
│   ├── template_walkthrough.md    # Бланк отчета о сдаче/демонстрации фичи
│   ├── template_pull_request.md   # Бланк описания Pull Request
│   ├── template_session_log.md    # Бланк отчета о сессии
│   ├── template_bug_report.md     # Бланк баг-репорта (Симптом ➔ Причина ➔ Решение)
│   ├── template_task.md           # Бланк карточки задачи
│   ├── template_adr.md            # Бланк архитектурного решения (ADR)
│   └── template_component_spec.md # Бланк спецификации компонента
│
├── architecture/                  # 🏗️ Архитектура и спецификации
│   ├── CODEBASE_MAP.md            # Карта кодовой базы и связи модулей
│   ├── SYSTEM_DESIGN.md           # Архитектура системы, стек и потоки данных
│   └── SECURITY_SPEC.md           # Модель безопасности, секреты, токены
│
├── decisions/                     # 🏛️ Архитектурные решения (ADR)
│   ├── README.md                  # Правила оформления ADR
│   └── ADR_000_example.md         # Эталонный пример архитектурного решения
│
├── bugs_and_fixes/                # 🐛 База знаний по ошибкам и багам
│   ├── README.md                  # Как фиксировать баги
│   └── BUG_000_example.md         # Эталонный пример оформления бага
│
├── tasks/                         # 📋 Управление задачами
│   ├── active_task.md             # Текущая задача с чек-листом
│   ├── backlog.md                 # Бэклог задач и идей на будущее
│   └── archive/                   # Архив выполненных задач
│
├── history/                       # 📝 Инкрементальный журнал сессий (Never Overwrite!)
│   ├── README.md                  # Правила ведения истории
│   └── session_000_init_example.md# Эталонный пример лога сессии
│
├── registry/                      # 👤 Реестр агентов и моделей
│   ├── README.md                  # Описание реестра
│   └── agent_profile_template.md  # Шаблон профиля агента
│
├── deployment/                    # 🚀 Развертывание
│   └── DEPLOYMENT_RUNBOOK.md      # Инструкции деплоя (Docker, Prod/Dev, SSL)
│
├── runbooks/                      # 🚑 Аварийный справочник
│   └── TROUBLESHOOTING.md         # Решение типичных сбоев (порты, БД, кэш)
│
├── testing/                       # 🧪 Тестирование и QA
│   └── QA_CHECKLIST.md            # Чек-лист проверки перед релизом
│
├── plans/                         # 📐 Большие планы разработки
├── walkthroughs/                  # 🚀 Отчеты о приемке и демонстрациях
│
└── tools/                         # 🛠️ Скрипты автоматизации (Python Standard Library)
    ├── brain.py                   # 🧠 Единый CLI-комбайн управления Вторым Мозгом
    ├── check_integrity.py         # Проверка целостности Second Brain (с флагом --fix)
    ├── init_project.py            # Автоматическая инициализация нового проекта
    ├── new_plan.py                # Мгновенная генерация нового плана (Plan-First)
    ├── dump_context.py            # Копирование контекста в буфер обмена для веб-чатов
    ├── end_session.py             # Автоматизация фиксации завершения сессии
    └── install_hooks.py           # Установка Git pre-commit хука для защиты репозитория
```
