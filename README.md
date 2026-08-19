# HH Monitor — аналитика рынка труда

Собирает вакансии hh.ru через официальный API, хранит в SQLite,
показывает аналитику на Flask-дашборде, формирует недельные
отчеты со сравнением к прошлой неделе.

## Компоненты
- collector.py — сбор вакансий (cron, каждый час, пн–пт 08:00–20:00 MSK)
- app.py — дашборд (127.0.0.1:5001, доступ только через SSH-туннель)
- weekly_report.py — недельный отчет (cron, пятница 20:05)
- database.py — схема SQLite
- templates/dashboard.html — дашборд (Chart.js, темная тема)

## Установка
1. python3 -m venv venv && source venv/bin/activate
2. pip install flask httpx python-dotenv pytz
3. Получить токены на dev.hh.ru (раздел ниже) и заполнить .env:
   HH_CLIENT_ID, HH_CLIENT_SECRET, HH_USER_AGENT
4. python database.py

## Получение токенов (обязательно, самостоятельно)

Каждый пользователь получает СОБСТВЕННЫЕ токены под своим аккаунтом:

1. Войдите на https://dev.hh.ru под своим аккаунтом hh.ru.
2. Зарегистрируйте приложение: имя + redirect URI
   (например, http://localhost:8080/callback).
3. Подайте заявку с описанием сценария: личное использование,
   только GET-запросы, данные не передаются третьим лицам.
   Рассмотрение занимает 1–7 дней.
4. После одобрения в карточке приложения появятся client_id и
   client_secret — внесите их в .env.

Важно: по условиям использования API hh.ru данные предназначены
только для личного использования. Не передавайте свои токены,
client_secret и базу данных третьим лицам.

## Настройка поиска под себя (обязательно)

Аналитика строится ТОЛЬКО по тем названиям вакансий, которые вы
укажете сами. Откройте collector.py и впишите свои названия в
словарь ROLE_GROUPS (кавычки сохраняйте — они дают точное совпадение):

ROLE_GROUPS = {
    "моя_роль": [
        '"название вакансии по-русски"',
        '"job title in english"',
    ],
}

Примеры:
- аналитик: '"data analyst"', '"аналитик данных"'
- разработчик: '"python developer"', '"разработчик python"'
- маркетолог: '"маркетолог"', '"performance marketer"'

В словаре SCOPES настраивается география и формат работы:
- {"area": "1"} — Москва
- {"schedule": "remote"} — удаленка

## Безопасность
- .env и база не коммитятся (.gitignore)
- Дашборд доступен только через SSH-туннель
- SSH только по ключу, UFW, fail2ban

## Мобильный доступ (HTTPS + пароль + fail2ban)

Для доступа с телефона из любой сети (не через SSH-туннель).
Все шаги выполняются один раз при развёртывании.

### 1. Самоподписанный SSL-сертификат

    mkdir -p /etc/nginx/ssl
    openssl req -x509 -nodes -days 730 -newkey rsa:2048 \
      -keyout /etc/nginx/ssl/hh-monitor.key \
      -out /etc/nginx/ssl/hh-monitor.crt \
      -subj "/CN=hh-monitor"
    chmod 600 /etc/nginx/ssl/hh-monitor.key

### 2. Nginx + пароль на страницу

    apt install -y nginx apache2-utils
    htpasswd -c /etc/nginx/.htpasswd monitor

Пароль придумайте надёжный, при вводе он не отображается.

### 3. Конфиг nginx

Создать файл /etc/nginx/sites-available/hh-monitor:

    server {
        listen 443 ssl;
        server_name _;

        ssl_certificate /etc/nginx/ssl/hh-monitor.crt;
        ssl_certificate_key /etc/nginx/ssl/hh-monitor.key;
        ssl_protocols TLSv1.2 TLSv1.3;

        auth_basic "HH Monitor";
        auth_basic_user_file /etc/nginx/.htpasswd;

        location / {
            proxy_pass http://127.0.0.1:5001;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }

Активировать:

    ln -sf /etc/nginx/sites-available/hh-monitor /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default
    nginx -t && systemctl restart nginx

### 4. Fail2ban (бан IP после 3 неудачных попыток входа)

Создать файл /etc/fail2ban/jail.d/hh-monitor.conf:

    [nginx-http-auth]
    enabled = true
    port = https
    filter = nginx-http-auth
    logpath = /var/log/nginx/error.log
    maxretry = 3
    findtime = 600
    bantime = 86400

Применить:

    systemctl restart fail2ban

Бан действует сутки. Разбанить свой IP, если ошиблись паролем:

    fail2ban-client set nginx-http-auth unbanip ВАШ_IP

### 5. Открыть порт в файрволе

    ufw allow 443/tcp
    ufw status

### Как заходить

С компьютера и с телефона: https://IP_СЕРВЕРА/

Браузер предупредит о самоподписанном сертификате — это нормально,
шифрование трафика работает. Нажмите «Дополнительно» → «Перейти на сайт».
Затем введите логин monitor и ваш пароль.

Проверка работы:

    curl -k -s -o /dev/null -w "%{http_code}\n" https://IP_СЕРВЕРА/
    curl -k -s -o /dev/null -w "%{http_code}\n" -u monitor:ВАШ_ПАРОЛЬ https://IP_СЕРВЕРА/

Первая команда должна вернуть 401 (без пароля не пускает), вторая — 200.
