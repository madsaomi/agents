# 🚀 Руководство по Развертыванию Проекта (DEPLOYMENT_RUNBOOK.md)

**Проект:** Second Brain Template  
Инструкции по сборке, настройке окружения и запуску сервиса в тестовой и производственной средах.

---

## 🛠️ 1. Локальный запуск для разработки (Development)

### Предварительные требования:
- Установленный рантайм (Python 3.10+ / Node.js 18+ / Docker).
- Git.

### Шаги запуска:
1. Клонировать репозиторий и перейти в корень проекта.
2. Скопировать `.env.example` в `.env`:
   ```bash
   cp .env.example .env
   ```
3. Заполнить необходимые переменные окружения в `.env`.
4. Установить зависимости:
   ```bash
   # Для Python:
   python -m venv venv
   source venv/bin/activate # или venv\Scripts\activate на Windows
   pip install -r requirements.txt

   # Для Node.js:
   npm install
   ```
5. Запустить в режиме разработки:
   ```bash
   # Python (FastAPI/Uvicorn):
   python -m uvicorn src.main:app --reload --port 8000

   # Node.js:
   npm run dev
   ```

---

## 🐳 2. Развертывание через Docker / Docker Compose (Рекомендуемый способ)

### Сборка и запуск:
```bash
# Собрать и запустить контейнеры в фоне
docker compose up -d --build

# Проверить статус контейнеров
docker compose ps

# Просмотр логов в реальном времени
docker compose logs -f
```

---

## 🌐 3. Развертывание на Linux сервере (Systemd + Nginx + Let's Encrypt SSL)

### Шаг 1: Настройка Systemd сервиса (Автозапуск 24/7)
Создать файл `/etc/systemd/system/Second Brain Template.service`:
```ini
[Unit]
Description=Second Brain Template Service
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/Second Brain Template
ExecStart=/var/www/Second Brain Template/venv/bin/python -m uvicorn src.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5
EnvironmentFile=/var/www/Second Brain Template/.env

[Install]
WantedBy=multi-user.target
```

Активировать и запустить:
```bash
sudo systemctl daemon-reload
sudo systemctl enable Second Brain Template
sudo systemctl start Second Brain Template
sudo systemctl status Second Brain Template
```

### Шаг 2: Настройка Nginx (Reverse Proxy)
Создать файл `/etc/nginx/sites-available/Second Brain Template`:
```nginx
server {
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```
Активировать конфигурацию:
```bash
sudo ln -s /etc/nginx/sites-available/Second Brain Template /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Шаг 3: Бесплатный SSL-сертификат (HTTPS)
```bash
sudo certbot --nginx -d yourdomain.com
```
Certbot автоматически сконфигурирует HTTPS и добавит автообновление сертификата.
