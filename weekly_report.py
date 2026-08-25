import json, os
from datetime import datetime, timedelta
import pytz
from database import get_db, MSK

def median(vals):
    vals = sorted(v for v in vals if v is not None)
    if not vals: return None
    n = len(vals); mid = n // 2
    return vals[mid] if n % 2 else round((vals[mid-1] + vals[mid]) / 2)

MONTHS_RU = {1:'января',2:'февраля',3:'марта',4:'апреля',5:'мая',6:'июня',
             7:'июля',8:'августа',9:'сентября',10:'октября',11:'ноября',12:'декабря'}
MGMT_MED_TO = 200000  # целевой уровень Head of Support: зарплата от 200K

now = datetime.now(MSK)
if now.weekday() == 6:  # воскресенье: финал за завершающуюся неделю
    week_start = (now - timedelta(days=6)).date()
    week_end = now.date()
else:  # пн–сб: снапшот последней ПОЛНОЙ недели, держится до воскресенья
    week_start = (now - timedelta(days=now.weekday() + 7)).date()
    week_end = week_start + timedelta(days=6)
ws_iso, we_iso = week_start.isoformat(), week_end.isoformat()
if week_start.month == week_end.month:
    date_range = f"{week_start.day}–{week_end.day} {MONTHS_RU[week_start.month]}"
else:
    date_range = f"{week_start.day} {MONTHS_RU[week_start.month]} – {week_end.day} {MONTHS_RU[week_end.month]}"

conn = get_db()

rows = conn.execute("""
    SELECT salary_from, salary_to FROM vacancies
    WHERE published_date BETWEEN ? AND ? AND (lower(name) LIKE '%поддержк%' OR lower(name) LIKE '%support%' OR lower(name) LIKE '%service desk%' OR lower(name) LIKE '%helpdesk%' OR lower(name) LIKE '%customer success%' OR lower(name) LIKE '%customer service%' OR lower(name) LIKE '%клиентского сервиса%' OR lower(name) LIKE '%itsm%' OR lower(name) LIKE '%сервис%' OR lower(name) LIKE '%service%' OR lower(name) LIKE '%care%' OR lower(name) LIKE '%мониторинг%' OR lower(name) LIKE '%1 линии%' OR lower(name) LIKE '%2 линии%' OR lower(name) LIKE '%1-й линии%' OR lower(name) LIKE '%2-й линии%' OR lower(name) LIKE '%первой линии%' OR lower(name) LIKE '%второй линии%' OR lower(name) LIKE '%1 line%' OR lower(name) LIKE '%2 line%' OR lower(name) LIKE '% l1%' OR lower(name) LIKE '% l2%' OR lower(name) LIKE '%l1 %' OR lower(name) LIKE '%l2 %' OR lower(name) LIKE '% line 1%' OR lower(name) LIKE '% line 2%' OR lower(name) LIKE '%line 1 %' OR lower(name) LIKE '%line 2 %' OR lower(name) LIKE '%сервиса поддержки%' OR lower(name) LIKE '%сервиса технической поддержки%' OR lower(name) LIKE '%service support%') AND lower(name) NOT LIKE '%руководитель ит отдела%' AND lower(name) NOT LIKE '%руководитель it отдела%' AND lower(name) NOT LIKE '%начальник ит отдела%' AND lower(name) NOT LIKE '%руководитель отдела информационных технологий%' AND salary_currency IN ('RUB','RUR')
""", (ws_iso, we_iso)).fetchall()

total = conn.execute("SELECT COUNT(*) as c FROM vacancies WHERE published_date BETWEEN ? AND ? AND (lower(name) LIKE '%поддержк%' OR lower(name) LIKE '%support%' OR lower(name) LIKE '%service desk%' OR lower(name) LIKE '%helpdesk%' OR lower(name) LIKE '%customer success%' OR lower(name) LIKE '%customer service%' OR lower(name) LIKE '%клиентского сервиса%' OR lower(name) LIKE '%itsm%' OR lower(name) LIKE '%сервис%' OR lower(name) LIKE '%service%' OR lower(name) LIKE '%care%' OR lower(name) LIKE '%мониторинг%' OR lower(name) LIKE '%1 линии%' OR lower(name) LIKE '%2 линии%' OR lower(name) LIKE '%1-й линии%' OR lower(name) LIKE '%2-й линии%' OR lower(name) LIKE '%первой линии%' OR lower(name) LIKE '%второй линии%' OR lower(name) LIKE '%1 line%' OR lower(name) LIKE '%2 line%' OR lower(name) LIKE '% l1%' OR lower(name) LIKE '% l2%' OR lower(name) LIKE '%l1 %' OR lower(name) LIKE '%l2 %' OR lower(name) LIKE '% line 1%' OR lower(name) LIKE '% line 2%' OR lower(name) LIKE '%line 1 %' OR lower(name) LIKE '%line 2 %' OR lower(name) LIKE '%сервиса поддержки%' OR lower(name) LIKE '%сервиса технической поддержки%' OR lower(name) LIKE '%service support%') AND lower(name) NOT LIKE '%руководитель ит отдела%' AND lower(name) NOT LIKE '%руководитель it отдела%' AND lower(name) NOT LIKE '%начальник ит отдела%' AND lower(name) NOT LIKE '%руководитель отдела информационных технологий%'", (ws_iso, we_iso)).fetchone()['c']
no_salary = conn.execute("SELECT COUNT(*) as c FROM vacancies WHERE published_date BETWEEN ? AND ? AND (lower(name) LIKE '%поддержк%' OR lower(name) LIKE '%support%' OR lower(name) LIKE '%service desk%' OR lower(name) LIKE '%helpdesk%' OR lower(name) LIKE '%customer success%' OR lower(name) LIKE '%customer service%' OR lower(name) LIKE '%клиентского сервиса%' OR lower(name) LIKE '%itsm%' OR lower(name) LIKE '%сервис%' OR lower(name) LIKE '%service%' OR lower(name) LIKE '%care%' OR lower(name) LIKE '%мониторинг%' OR lower(name) LIKE '%1 линии%' OR lower(name) LIKE '%2 линии%' OR lower(name) LIKE '%1-й линии%' OR lower(name) LIKE '%2-й линии%' OR lower(name) LIKE '%первой линии%' OR lower(name) LIKE '%второй линии%' OR lower(name) LIKE '%1 line%' OR lower(name) LIKE '%2 line%' OR lower(name) LIKE '% l1%' OR lower(name) LIKE '% l2%' OR lower(name) LIKE '%l1 %' OR lower(name) LIKE '%l2 %' OR lower(name) LIKE '% line 1%' OR lower(name) LIKE '% line 2%' OR lower(name) LIKE '%line 1 %' OR lower(name) LIKE '%line 2 %' OR lower(name) LIKE '%сервиса поддержки%' OR lower(name) LIKE '%сервиса технической поддержки%' OR lower(name) LIKE '%service support%') AND lower(name) NOT LIKE '%руководитель ит отдела%' AND lower(name) NOT LIKE '%руководитель it отдела%' AND lower(name) NOT LIKE '%начальник ит отдела%' AND lower(name) NOT LIKE '%руководитель отдела информационных технологий%' AND salary_from IS NULL AND salary_to IS NULL", (ws_iso, we_iso)).fetchone()['c']
no_salary_pct = round(no_salary * 100 / total, 1) if total else 0
closed = conn.execute("SELECT COUNT(*) as c FROM vacancies WHERE published_date BETWEEN ? AND ? AND (lower(name) LIKE '%поддержк%' OR lower(name) LIKE '%support%' OR lower(name) LIKE '%service desk%' OR lower(name) LIKE '%helpdesk%' OR lower(name) LIKE '%customer success%' OR lower(name) LIKE '%customer service%' OR lower(name) LIKE '%клиентского сервиса%' OR lower(name) LIKE '%itsm%' OR lower(name) LIKE '%сервис%' OR lower(name) LIKE '%service%' OR lower(name) LIKE '%care%' OR lower(name) LIKE '%мониторинг%' OR lower(name) LIKE '%1 линии%' OR lower(name) LIKE '%2 линии%' OR lower(name) LIKE '%1-й линии%' OR lower(name) LIKE '%2-й линии%' OR lower(name) LIKE '%первой линии%' OR lower(name) LIKE '%второй линии%' OR lower(name) LIKE '%1 line%' OR lower(name) LIKE '%2 line%' OR lower(name) LIKE '% l1%' OR lower(name) LIKE '% l2%' OR lower(name) LIKE '%l1 %' OR lower(name) LIKE '%l2 %' OR lower(name) LIKE '% line 1%' OR lower(name) LIKE '% line 2%' OR lower(name) LIKE '%line 1 %' OR lower(name) LIKE '%line 2 %' OR lower(name) LIKE '%сервиса поддержки%' OR lower(name) LIKE '%сервиса технической поддержки%' OR lower(name) LIKE '%service support%') AND lower(name) NOT LIKE '%руководитель ит отдела%' AND lower(name) NOT LIKE '%руководитель it отдела%' AND lower(name) NOT LIKE '%начальник ит отдела%' AND lower(name) NOT LIKE '%руководитель отдела информационных технологий%' AND archived=1", (ws_iso, we_iso)).fetchone()['c']
closed_pct = round(closed * 100 / total, 1) if total else 0

target = conn.execute("SELECT COUNT(*) as c FROM vacancies WHERE published_date BETWEEN ? AND ? AND (lower(name) LIKE '%поддержк%' OR lower(name) LIKE '%support%' OR lower(name) LIKE '%service desk%' OR lower(name) LIKE '%helpdesk%' OR lower(name) LIKE '%customer success%' OR lower(name) LIKE '%customer service%' OR lower(name) LIKE '%клиентского сервиса%' OR lower(name) LIKE '%itsm%' OR lower(name) LIKE '%сервис%' OR lower(name) LIKE '%service%' OR lower(name) LIKE '%care%' OR lower(name) LIKE '%мониторинг%' OR lower(name) LIKE '%1 линии%' OR lower(name) LIKE '%2 линии%' OR lower(name) LIKE '%1-й линии%' OR lower(name) LIKE '%2-й линии%' OR lower(name) LIKE '%первой линии%' OR lower(name) LIKE '%второй линии%' OR lower(name) LIKE '%1 line%' OR lower(name) LIKE '%2 line%' OR lower(name) LIKE '% l1%' OR lower(name) LIKE '% l2%' OR lower(name) LIKE '%l1 %' OR lower(name) LIKE '%l2 %' OR lower(name) LIKE '% line 1%' OR lower(name) LIKE '% line 2%' OR lower(name) LIKE '%line 1 %' OR lower(name) LIKE '%line 2 %' OR lower(name) LIKE '%сервиса поддержки%' OR lower(name) LIKE '%сервиса технической поддержки%' OR lower(name) LIKE '%service support%') AND lower(name) NOT LIKE '%руководитель ит отдела%' AND lower(name) NOT LIKE '%руководитель it отдела%' AND lower(name) NOT LIKE '%начальник ит отдела%' AND lower(name) NOT LIKE '%руководитель отдела информационных технологий%' AND salary_to >= ?", (ws_iso, we_iso, MGMT_MED_TO)).fetchone()['c']

med_from = median([r['salary_from'] for r in rows])
med_to = median([r['salary_to'] for r in rows])

top_companies = conn.execute("SELECT employer_name FROM vacancies WHERE published_date BETWEEN ? AND ? AND (lower(name) LIKE '%поддержк%' OR lower(name) LIKE '%support%' OR lower(name) LIKE '%service desk%' OR lower(name) LIKE '%helpdesk%' OR lower(name) LIKE '%customer success%' OR lower(name) LIKE '%customer service%' OR lower(name) LIKE '%клиентского сервиса%' OR lower(name) LIKE '%itsm%' OR lower(name) LIKE '%сервис%' OR lower(name) LIKE '%service%' OR lower(name) LIKE '%care%' OR lower(name) LIKE '%мониторинг%' OR lower(name) LIKE '%1 линии%' OR lower(name) LIKE '%2 линии%' OR lower(name) LIKE '%1-й линии%' OR lower(name) LIKE '%2-й линии%' OR lower(name) LIKE '%первой линии%' OR lower(name) LIKE '%второй линии%' OR lower(name) LIKE '%1 line%' OR lower(name) LIKE '%2 line%' OR lower(name) LIKE '% l1%' OR lower(name) LIKE '% l2%' OR lower(name) LIKE '%l1 %' OR lower(name) LIKE '%l2 %' OR lower(name) LIKE '% line 1%' OR lower(name) LIKE '% line 2%' OR lower(name) LIKE '%line 1 %' OR lower(name) LIKE '%line 2 %' OR lower(name) LIKE '%сервиса поддержки%' OR lower(name) LIKE '%сервиса технической поддержки%' OR lower(name) LIKE '%service support%') AND lower(name) NOT LIKE '%руководитель ит отдела%' AND lower(name) NOT LIKE '%руководитель it отдела%' AND lower(name) NOT LIKE '%начальник ит отдела%' AND lower(name) NOT LIKE '%руководитель отдела информационных технологий%' AND employer_name IS NOT NULL GROUP BY employer_name ORDER BY COUNT(*) DESC LIMIT 5", (ws_iso, we_iso)).fetchall()
top_skills = conn.execute("SELECT skill_name as name, COUNT(*) as c FROM vacancy_skills s JOIN vacancies v ON v.id=s.vacancy_id WHERE v.published_date BETWEEN ? AND ? AND (lower(name) LIKE '%поддержк%' OR lower(name) LIKE '%support%' OR lower(name) LIKE '%service desk%' OR lower(name) LIKE '%helpdesk%' OR lower(name) LIKE '%customer success%' OR lower(name) LIKE '%customer service%' OR lower(name) LIKE '%клиентского сервиса%' OR lower(name) LIKE '%itsm%' OR lower(name) LIKE '%сервис%' OR lower(name) LIKE '%service%' OR lower(name) LIKE '%care%' OR lower(name) LIKE '%мониторинг%' OR lower(name) LIKE '%1 линии%' OR lower(name) LIKE '%2 линии%' OR lower(name) LIKE '%1-й линии%' OR lower(name) LIKE '%2-й линии%' OR lower(name) LIKE '%первой линии%' OR lower(name) LIKE '%второй линии%' OR lower(name) LIKE '%1 line%' OR lower(name) LIKE '%2 line%' OR lower(name) LIKE '% l1%' OR lower(name) LIKE '% l2%' OR lower(name) LIKE '%l1 %' OR lower(name) LIKE '%l2 %' OR lower(name) LIKE '% line 1%' OR lower(name) LIKE '% line 2%' OR lower(name) LIKE '%line 1 %' OR lower(name) LIKE '%line 2 %' OR lower(name) LIKE '%сервиса поддержки%' OR lower(name) LIKE '%сервиса технической поддержки%' OR lower(name) LIKE '%service support%') AND lower(name) NOT LIKE '%руководитель ит отдела%' AND lower(name) NOT LIKE '%руководитель it отдела%' AND lower(name) NOT LIKE '%начальник ит отдела%' AND lower(name) NOT LIKE '%руководитель отдела информационных технологий%' AND v.archived=0 GROUP BY skill_name ORDER BY c DESC LIMIT 8", (ws_iso, we_iso)).fetchall()
experience = conn.execute("SELECT experience_name as name, COUNT(*) as c FROM vacancies WHERE published_date BETWEEN ? AND ? AND (lower(name) LIKE '%поддержк%' OR lower(name) LIKE '%support%' OR lower(name) LIKE '%service desk%' OR lower(name) LIKE '%helpdesk%' OR lower(name) LIKE '%customer success%' OR lower(name) LIKE '%customer service%' OR lower(name) LIKE '%клиентского сервиса%' OR lower(name) LIKE '%itsm%' OR lower(name) LIKE '%сервис%' OR lower(name) LIKE '%service%' OR lower(name) LIKE '%care%' OR lower(name) LIKE '%мониторинг%' OR lower(name) LIKE '%1 линии%' OR lower(name) LIKE '%2 линии%' OR lower(name) LIKE '%1-й линии%' OR lower(name) LIKE '%2-й линии%' OR lower(name) LIKE '%первой линии%' OR lower(name) LIKE '%второй линии%' OR lower(name) LIKE '%1 line%' OR lower(name) LIKE '%2 line%' OR lower(name) LIKE '% l1%' OR lower(name) LIKE '% l2%' OR lower(name) LIKE '%l1 %' OR lower(name) LIKE '%l2 %' OR lower(name) LIKE '% line 1%' OR lower(name) LIKE '% line 2%' OR lower(name) LIKE '%line 1 %' OR lower(name) LIKE '%line 2 %' OR lower(name) LIKE '%сервиса поддержки%' OR lower(name) LIKE '%сервиса технической поддержки%' OR lower(name) LIKE '%service support%') AND lower(name) NOT LIKE '%руководитель ит отдела%' AND lower(name) NOT LIKE '%руководитель it отдела%' AND lower(name) NOT LIKE '%начальник ит отдела%' AND lower(name) NOT LIKE '%руководитель отдела информационных технологий%' AND archived=0 AND experience_name IS NOT NULL GROUP BY experience_name ORDER BY c DESC", (ws_iso, we_iso)).fetchall()

prev = conn.execute("SELECT total_vacancies, med_salary_from, med_salary_to FROM weekly_reports WHERE week_start < ? ORDER BY week_start DESC LIMIT 1", (ws_iso,)).fetchone()

conn.execute("DELETE FROM weekly_reports WHERE week_start = ?", (ws_iso,))
conn.execute("""INSERT INTO weekly_reports (week_start, week_end, total_vacancies, avg_salary_from, avg_salary_to, med_salary_from, med_salary_to, top_companies, created_at) VALUES (?,?,?,?,?,?,?,?,?)""",
    (ws_iso, we_iso, total, None, None, med_from, med_to,
     json.dumps([r['employer_name'] for r in top_companies], ensure_ascii=False),
     datetime.now(MSK).isoformat()))
conn.commit()

# --- Автокомментарий аналитика ---
def build_comment():
    parts = []
    if med_to:
        if med_to < MGMT_MED_TO:
            t_pct = round(target * 100 / total, 1) if total else 0
            parts.append(f"медиана «до» {round(med_to/1000)}K ниже целевого уровня {round(MGMT_MED_TO/1000)}K+ — выборка чистая (руководящая поддержка); 200K+ — верхний квартиль, его достигают лишь {target} вакансий ({t_pct}%) за неделю дотягивают до 200K+")
        else:
            parts.append(f"медиана «до» {round(med_to/1000)}K соответствует целевому уровню {round(MGMT_MED_TO/1000)}K+")
    if no_salary_pct > 50:
        parts.append(f"большинство работодателей ({no_salary_pct}%) не публикуют вилку — реальные предложения выше опубликованных")
    elif no_salary_pct > 25:
        parts.append(f"прозрачность зарплат средняя: {no_salary_pct}% вакансий без вилки")
    if prev:
        if prev['total_vacancies']:
            d = round((total - prev['total_vacancies']) * 100 / prev['total_vacancies'], 1)
            if d > 10: parts.append(f"спрос вырос на {d}% к прошлой неделе")
            elif d < -10: parts.append(f"спрос снизился на {abs(d)}% к прошлой неделе")
            else: parts.append(f"спрос на уровне прошлой недели ({d:+.1f}%)")
        if prev['med_salary_to'] and med_to:
            dm = round((med_to - prev['med_salary_to']) * 100 / prev['med_salary_to'], 1)
            if dm > 5: parts.append(f"медиана «до» поднялась на {dm}%")
            elif dm < -5: parts.append(f"медиана «до» просела на {abs(dm)}%")
    if experience:
        tot_exp = sum(r['c'] for r in experience)
        top = experience[0]
        if tot_exp:
            parts.append(f"основной спрос — опыт «{top['name']}» ({round(top['c']*100/tot_exp)}%)")
    return '. '.join(p.capitalize() for p in parts) + '.'

# Ручная заметка (если есть файл) — добавляется после автокомментария
NOTE = '/var/www/presentations/weekly_note.txt'
manual = open(NOTE).read().strip() if os.path.exists(NOTE) else ''

comment = build_comment() + ((' ' + manual) if manual else '')

def skill_list_html(): return '\n'.join(f'<li>{r["name"]} — {r["c"]}</li>' for r in top_skills)
def exp_list_html():
    t = sum(r['c'] for r in experience)
    return '\n'.join(f'<li>{r["name"]} — {round(r["c"]*100/t) if t else 0}%</li>' for r in experience)
def comp_list_html(): return '\n'.join(f'<li>{n}</li>' for n in [r['employer_name'] for r in top_companies])

n_paid = max(len(rows), 1)
c_to = sum(1 for r in rows if (r['salary_to'] or 0) >= 200000)
c_from = sum(1 for r in rows if (r['salary_from'] or 0) >= 200000)
if med_from and med_to:
    spread = round((med_to - med_from) / med_from * 100)
    oot = (f"медиана «от» {round(med_from/1000)}K, «до» {round(med_to/1000)}K, разрыв вилки {spread}%. "
           f"Ролей с «до» ≥ 200K: {c_to} из {len(rows)} ({round(c_to*100/n_paid)}%); с «от» ≥ 200K: {c_from} ({round(c_from*100/n_paid)}%). "
           + ("Нижняя граница типичной вилки уже выше цели 200K+." if med_from >= 200000 else "Цель 200K+ достижима на верхней границе вилки."))
else:
    oot = "мало данных о зарплатах за неделю для анализа «от–до»."
med_range_k = f"{round(med_from/1000)}–{round(med_to/1000)}K" if med_from and med_to else "—"

html = f"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="UTF-8">
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ background:#0b1121; color:#f1f5f9; font-family:-apple-system,"Segoe UI",Roboto,Arial,sans-serif; padding:40px; }}
  .wrap {{ max-width:1000px; margin:0 auto; }}
  h1 {{ font-size:30px; margin-bottom:6px; }}
  .sub {{ color:#94a3b8; font-size:15px; margin-bottom:24px; }}
  .grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:14px; margin-bottom:24px; }}
  .m {{ background:#151e32; border:1px solid #1e293b; border-radius:14px; padding:18px; text-align:center; }}
  .m .v {{ font-size:26px; font-weight:800; color:#60a5fa; }}
  .m .l {{ font-size:12px; color:#94a3b8; margin-top:4px; }}
  .cols {{ display:grid; grid-template-columns:1fr 1fr 1fr; gap:14px; margin-bottom:24px; }}
  .card {{ background:#151e32; border:1px solid #1e293b; border-radius:14px; padding:20px; }}
  h3 {{ font-size:16px; margin-bottom:12px; }}
  li {{ list-style:none; padding:6px 0; border-bottom:1px solid #1e293b; font-size:14px; color:#cbd5e1; }}
  .out {{ background:#151e32; border:1px solid #3b82f6; border-radius:14px; padding:18px; font-size:15px; line-height:1.6; }}
  .out b {{ color:#60a5fa; }}
</style></head><body><div class="wrap">
  <h1>📊 Head of Support / Team Lead — неделя {date_range}</h1>
  <p class="sub">Недельный KPI HH Monitor · обновлено {datetime.now(MSK).strftime("%d.%m.%Y %H:%M")}</p>
  <div class="grid">
    <div class="m"><div class="v">{total}</div><div class="l">вакансий за неделю</div></div>
    <div class="m"><div class="v">{closed_pct}%</div><div class="l">уже закрыты ({closed})</div></div>
    <div class="m"><div class="v">{no_salary_pct}%</div><div class="l">без указания зарплаты</div></div>
    <div class="m"><div class="v">{med_range_k}</div><div class="l">медиана «от–до», ₽</div></div>
  </div>
  <div class="cols">
    <div class="card"><h3>🧱 Топ навыков</h3><ul>{skill_list_html()}</ul></div>
    <div class="card"><h3>👥 Опыт</h3><ul>{exp_list_html()}</ul></div>
    <div class="card"><h3>🏢 Топ компаний</h3><ul>{comp_list_html()}</ul></div>
  </div>
  <div class="out"><b>📌 Итоги недели:</b> {comment}</div>
  <div class="out" style="margin-top:14px;border-color:#334155"><b>💰 Анализ «от–до»:</b> {oot}</div>
</div></body></html>
"""

import sys
import os
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reports', 'weekly.html')
with open(OUT, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"[{datetime.now(MSK)}] Weekly KPI: {ws_iso}-{we_iso} total={total} med={med_from}-{med_to}")
print(f"Comment: {comment}")
conn.close()
