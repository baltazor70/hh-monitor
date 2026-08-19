import json
from datetime import datetime, timedelta
import pytz
from database import get_db, MSK

now = datetime.now(MSK)
monday = (now - timedelta(days=now.weekday())).date()
week_start = monday
week_end = monday + timedelta(days=4)

conn = get_db()

def week_stats(s, e):
    return conn.execute("""
        SELECT COUNT(*) as total,
               ROUND(AVG(CASE WHEN salary_currency IN ('RUB','RUR') THEN salary_from END)) as avg_from,
               ROUND(AVG(CASE WHEN salary_currency IN ('RUB','RUR') THEN salary_to END)) as avg_to
        FROM vacancies WHERE published_date BETWEEN ? AND ?
    """, (s.isoformat(), e.isoformat())).fetchone()

cur = week_stats(week_start, week_end)

top = conn.execute("""
    SELECT employer_name FROM vacancies
    WHERE published_date BETWEEN ? AND ? AND employer_name IS NOT NULL
    GROUP BY employer_name ORDER BY COUNT(*) DESC LIMIT 5
""", (week_start.isoformat(), week_end.isoformat())).fetchall()

# Удаляем старый отчет за эту же неделю (идемпотентность)
conn.execute("DELETE FROM weekly_reports WHERE week_start = ?", (week_start.isoformat(),))

conn.execute("""
    INSERT INTO weekly_reports (week_start, week_end, total_vacancies,
        avg_salary_from, avg_salary_to, top_companies, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
""", (
    week_start.isoformat(), week_end.isoformat(),
    cur['total'], cur['avg_from'], cur['avg_to'],
    json.dumps([r['employer_name'] for r in top], ensure_ascii=False),
    datetime.now(MSK).isoformat()
))

conn.commit()
conn.close()
print(f"[{datetime.now(MSK)}] Weekly report saved: {week_start} - {week_end}, total={cur['total']}")
