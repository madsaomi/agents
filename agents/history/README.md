# 📝 Непрерывный Журнал Сессий (Session History)

Каталог предназначен для сохранения пошаговой хронологии работы всех агентов над проектом.

---

## ⚡ СТРОЖАЙШЕЕ ПРАВИЛО: NEVER OVERWRITE
> **СТРОГО ЗАПРЕЩЕНО** перезаписывать, изменять или удалять старые файлы сессий!  
> В конце каждой рабочей сессии агент **ОБЯЗАН** создать **НОВЫЙ** файл.

---

## 📋 Формат именования файлов:
```
session_YYYY-MM-DD_NN_<agent_short_name>.md
```
Например:
- `session_2026-09-18_01_init.md`
- `session_2026-09-18_02_auth_system.md`
- `session_2026-09-19_01_ui_redesign.md`

Шаблон для заполнения находится в: [`agents/templates/template_session_log.md`](../templates/template_session_log.md).
Пример заполнения можно посмотреть в: [`session_000_init_example.md`](session_000_init_example.md).
