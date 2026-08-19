# HH Monitor — аналитика рынка труда (Head of Support / Team Lead)

Собирает вакансии hh.ru через официальный API (OAuth, client_credentials),
хранит в SQLite, показывает аналитику на Flask-дашборде,
формирует недельные отчеты со сравнением к прошлой неделе.

## Компоненты
- collector.py — сбор вакансий (cron, каждый час, пн–пт 08:00–20:00 MSK)
- app.py — дашборд (127.0.0.1:5001, доступ только через SSH-туннель)
- weekly_report.py — недельный отчет (cron, пятница 20:05)
- database.py — схема SQLite
- templates/dashboard.html — дашборд (Chart.js, темная тема)

## Установка
1. python3 -m venv venv && source venv/bin/activate
2. pip install flask httpx python-dotenv pytz
3. Заполнить .env: HH_CLIENT_ID, HH_CLIENT_SECRET, HH_USER_AGENT
4. python database.py

## Безопасность
- .env и база не коммитятся (.gitignore)
- Дашборд доступен только через SSH-туннель
- SSH только по ключу, UFW, fail2ban
