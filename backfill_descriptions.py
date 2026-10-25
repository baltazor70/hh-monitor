#!/usr/bin/env python3
"""
Бэкфилл описаний только для вакансий, попадающих в KPI на дашборде.
Фильтр повторяет запросы дашборда: те же ключевые слова, та же неделя, без архива.
"""
import time
from database import get_db
from collector import fetch_vacancy_full, get_access_token

# Ключевые слова поддержки — должны совпадать с app.py
SUPPORT_KEYWORDS = (
    'поддержк', 'сопровожден', 'эксплуатаци', 'мониторинг',
    'helpdesk', 'help desk', 'service desk', 'servicedesk',
    'сервис', 'сервиса', 'сервисной', 'сервисную',
    'клиентского сервиса', 'клиентский сервис',
    'поддержки пользователей', 'поддержку пользователей',
    'отдел ит', 'отдела ит', 'ит отдела', 'ит-отдела', 'отдел it', 'отдела it',
    'инфраструктур', 'support', 'tech support', 'application support',
)

# Исключения по названию (как на дашборде)
EXCLUDE_TITLE = (
    'руководитель ит отдела', 'руководитель it отдела',
    'начальник ит отдела', 'руководитель отдела информационных технологий',
)

def build_filter():
    like = " OR ".join(f"lower(name) LIKE '%{kw}%'" for kw in SUPPORT_KEYWORDS)
    notlike = " AND ".join(f"lower(name) NOT LIKE '%{kw}%'" for kw in EXCLUDE_TITLE)
    return like, notlike

def main():
    conn = get_db()
    token = get_access_token()
    if not token:
        print('Не удалось получить токен')
        return

    like, notlike = build_filter()

    # Выборка: только релевантные вакансии за последние 7 дней, попадающие в KPI
    query = f"""
        SELECT id, name
        FROM vacancies
        WHERE archived = 0
          AND skip_reason IS NULL
          AND is_duplicate = 0
          AND published_date >= date('now', '-7 days')
          AND ({like})
          AND {notlike}
          AND (description IS NULL OR TRIM(description) = '')
        ORDER BY published_date DESC
    """

    rows = conn.execute(query).fetchall()

    if not rows:
        print('Нет вакансий в KPI-выборке без описания')
        conn.close()
        return

    print(f'Вакансий в KPI без описания: {len(rows)}')
    for vid, name in rows:
        print(f'  - {name}')

    done = 0
    empty = 0

    for vid, name in rows:
        full = fetch_vacancy_full(token, vid)

        if full is None:
            time.sleep(5)
            continue

        desc = full.get('description') or ''
        conn.execute(
            "UPDATE vacancies SET description = ? WHERE id = ?",
            (desc, vid)
        )

        if not desc.strip():
            conn.execute(
                "UPDATE vacancies SET skip_reason = 'no_description' WHERE id = ? AND skip_reason IS NULL",
                (vid,)
            )
            empty += 1
            print(f'  [no_description] {name}')
        else:
            print(f'  [OK] {name} ({len(desc)} симв.)')

        conn.commit()
        done += 1

        # Длинная пауза между запросами
        time.sleep(3)

    conn.close()
    print(f'Обработано: {done}, пустых: {empty}')

if __name__ == '__main__':
    main()
