# 🐛 BUG-002: `index_memory` пишет индекс в расположение модуля, игнорируя root

- **Дата обнаружения:** 2026-11-01 10:43
- **Статус:** 🟢 РЕШЕНО
- **Затронутый файл / компонент:** `agents/tools/search.py::index_memory` (вызывается из `brain.py search --reindex`)
- **Обнаружил агент:** ZCode (GLM-5.3-Flash) — смок-тестом CLI из PLAN-009

---

## 🔍 1. Симптом (Что произошло)

Смок-тест `test_cli.py` запускал `python brain.py search --reindex` с `cwd=tmp`-скелетом
(2 файла памяти). Тест ожидал появление `.brain_index.db` в tmp — файла там не было.
Параллельно mtime `.brain_index.db` **живого репозитория** обновился, а сам индекс
был перезаписан единственной записью из tmp-скелета (`index_memory` удаляет записи
о несуществующих файлах → реальный индекс из 36 документов оказался затёрт).

```text
AssertionError: False is not true   # (tmp / ".brain_index.db").exists()
# при этом: "✅ Переиндексировано: 1 документов → .brain_index.db"  (rc=0)
```

---

## 🔬 2. Первопричина (Root Cause — ПОЧЕМУ это произошло)

`index_memory(root=...)` корректно резолвил `target_root` для **сканируемых файлов**
(`_iter_memory_files(target_root)`), но соединение с БД открывал через
`_connect(db_path)`, который при `db_path=None` берёт **модульную** константу
`INDEX_FILE = PROJECT_ROOT / ".brain_index.db"` (расположение модуля, не cwd).
В dev-режиме из корня репозитория модульный и cwd-корни совпадают — баг был
невидим. При запуске из другого каталога (cwd-проект с `agents/`, установленный
пакет) `brain.py` детектит root по cwd, но индекс писался/перезаписывался в
расположении модуля. `search_memory` уже делал правильно
(`db = target_root / INDEX_FILE.name`) — `index_memory` просто отставал.

---

## 🛠️ 3. Решение (Как исправлено)

`agents/tools/search.py::index_memory` — БД резолвится от `target_root`
(идентично `search_memory`); все существующие вызовы с явным `db_path`
(тесты, внутренние вызовы search.py) не затронуты:

```python
target_root = Path(root) if root else PROJECT_ROOT
db = Path(db_path) if db_path else (target_root / INDEX_FILE.name)
conn = _connect(db)
```

Пострадавший индекс живого репозитория восстановлен: `python brain.py search --reindex`
(36 документов). Регресс закрыт смок-тестом `test_root_detection_by_cwd`.

---

## 🛡️ 4. Правило предотвращения (Prevention Rule)

1. Любая функция с параметром `root` обязана резолвить **все** свои артефакты
   (БД, кэши, временные файлы) от этого root, а не от модульных констант;
   модульная константа допустима только как fallback при `root=None`.
2. Смок-тесты мутирующих команд запускать только из tmp-скелета с `cwd=tmp` —
   и проверять, что артефакт появился именно в tmp (этот тест и поймал баг).
3. При добавлении новой команды в `brain.py` проверять цепочку
   `PROJECT_ROOT → tool-function → файловые операции` на «протечки» модульных путей.
