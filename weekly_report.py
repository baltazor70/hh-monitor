import json
from datetime import datetime, timedelta
import pytz
from database import get_db, MSK

def median(vals):
    vals = sorted(v for v in vals if v is not None)
    if not vals: return None
    n = len(vals); mid = n // 2
    return vals[mid] if n % 2 else round((vals[mid-1] + vals[mid]) / 2)

now = datetime.now(MSK)
monday = (now - timedelta(days=now.weekday())).date()
week_start, week_end = monday, monday + timedelta(days=4)

conn = get_db()

rows = conn.execute("""
    SELECT salary_from, salary_to FROM vacancies
    WHERE published_date BETWEEN ? AND ? AND salary_currency IN ('RUB','RUR')
""", (week_start.isoformat(), week_end.isoformat())).fetchall()

total = conn.execute("""
    SELECT COUNT(*) as c FROM vacancies WHERE published_date BETWEEN ? AND ?
""", (week_start.isoformat(), week_end.isoformat())).fetchone()['c']

avg_from = round(sum(r['salary_from'] for r in rows if r['salary_from'])/len([r for r in rows if r['salary_from']])) if [r for r in rows if r['salary_from']] else None
avg_to = round(sum(r['salary_to'] for r in rows if r['salary_to'])/len([r for r in rows if r['salary_to']])) if [r for r in rows if r['salary_to']] else None
med_from = median([r['salary_from'] for r in rows])
med_to = median([r['salary_to'] for r in rows])

top = conn.execute("""
    SELECT employer_name FROM vacancies
    WHERE published_date BETWEEN ? AND ? AND employer_name IS NOT NULL
    GROUP BY employer_name ORDER BY COUNT(*) DESC LIMIT 5
""", (week_start.isoformat(), week_end.isoformat())).fetchall()

conn.execute("DELETE FROM weekly_reports WHERE week_start = ?", (week_start.isoformat(),))
conn.execute("""
    INSERT INTO weekly_reports (week_start, week_end, total_vacancies,
        avg_salary_from, avg_salary_to, med_salary_from, med_salary_to, top_companies, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (week_start.isoformat(), week_end.isoformat(), total,
      avg_from, avg_to, med_from, med_to,
      json.dumps([r['employer_name'] for r in top], ensure_ascii=False),
      datetime.now(MSK).isoformat()))

conn.commit(); conn.close()
print(f"[{datetime.now(MSK)}] Weekly report: {week_start}-{week_end} total={total} med_from={med_from} med_to={med_to}")
