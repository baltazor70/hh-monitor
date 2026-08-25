import sqlite3
from datetime import datetime, timedelta
import pytz
from flask import Flask, render_template, jsonify

DB_PATH = '/opt/hh-monitor/hh_monitor.db'
MSK = pytz.timezone('Europe/Moscow')
app = Flask(__name__)

def get_db():
    conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row; return conn

def median(vals):
    vals = sorted(v for v in vals if v is not None)
    if not vals: return None
    n = len(vals); mid = n // 2
    return vals[mid] if n % 2 else round((vals[mid-1] + vals[mid]) / 2)

def pct(cur, prev):
    if cur is None or prev is None or prev == 0: return None
    return round((cur - prev) / prev * 100, 1)

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/api/stats')
def stats():
    conn = get_db()
    now = datetime.now(MSK)
    today = now.date().isoformat()
    yesterday = (now - timedelta(days=1)).date().isoformat()
    cutoff = (now - timedelta(days=7)).date().isoformat()
    monday = (now - timedelta(days=now.weekday())).date().isoformat()

    counts_rows = conn.execute("""
        SELECT published_date as d, COUNT(*) as total
        FROM vacancies WHERE published_date >= ? AND (lower(name) LIKE '%поддержк%' OR lower(name) LIKE '%support%' OR lower(name) LIKE '%service desk%' OR lower(name) LIKE '%helpdesk%' OR lower(name) LIKE '%customer success%' OR lower(name) LIKE '%customer service%' OR lower(name) LIKE '%клиентского сервиса%' OR lower(name) LIKE '%itsm%') AND lower(name) NOT LIKE '%руководитель ит отдела%' AND lower(name) NOT LIKE '%руководитель it отдела%' AND lower(name) NOT LIKE '%начальник ит отдела%' AND lower(name) NOT LIKE '%руководитель отдела информационных технологий%' AND archived=0
        GROUP BY published_date
    """, (cutoff,)).fetchall()
    counts_by = {r['d']: r['total'] for r in counts_rows}

    sal_rows = conn.execute("""
        SELECT published_date as d, salary_from, salary_to FROM vacancies
        WHERE published_date >= ? AND (lower(name) LIKE '%поддержк%' OR lower(name) LIKE '%support%' OR lower(name) LIKE '%service desk%' OR lower(name) LIKE '%helpdesk%' OR lower(name) LIKE '%customer success%' OR lower(name) LIKE '%customer service%' OR lower(name) LIKE '%клиентского сервиса%' OR lower(name) LIKE '%itsm%') AND lower(name) NOT LIKE '%руководитель ит отдела%' AND lower(name) NOT LIKE '%руководитель it отдела%' AND lower(name) NOT LIKE '%начальник ит отдела%' AND lower(name) NOT LIKE '%руководитель отдела информационных технологий%' AND archived=0 AND salary_currency IN ('RUB','RUR')
    """, (cutoff,)).fetchall()
    by_day = {}
    for r in sal_rows:
        by_day.setdefault(r['d'], {'f': [], 't': []})
        if r['salary_from'] is not None: by_day[r['d']]['f'].append(r['salary_from'])
        if r['salary_to'] is not None: by_day[r['d']]['t'].append(r['salary_to'])

    labels, counts, med_from_l, med_to_l = [], [], [], []
    for i in range(7):
        d = (now - timedelta(days=6 - i)).date().isoformat()
        labels.append(d)
        counts.append(counts_by.get(d, 0))
        med_from_l.append(median(by_day.get(d, {})['f']) if d in by_day else None)
        med_to_l.append(median(by_day.get(d, {})['t']) if d in by_day else None)

    # продлеваем линии: день без данных держит предыдущее значение
    for lst in (med_from_l, med_to_l):
        last = None
        for i, v in enumerate(lst):
            if v is None:
                lst[i] = last
            else:
                last = v
    # заполняем начало недели первым известным значением
    for lst in (med_from_l, med_to_l):
        last = None
        for i in range(len(lst) - 1, -1, -1):
            if lst[i] is None:
                lst[i] = last
            else:
                last = lst[i]

    new_today = conn.execute("SELECT COUNT(*) as c FROM vacancies WHERE published_date=? AND (lower(name) LIKE '%поддержк%' OR lower(name) LIKE '%support%' OR lower(name) LIKE '%service desk%' OR lower(name) LIKE '%helpdesk%' OR lower(name) LIKE '%customer success%' OR lower(name) LIKE '%customer service%' OR lower(name) LIKE '%клиентского сервиса%' OR lower(name) LIKE '%itsm%') AND lower(name) NOT LIKE '%руководитель ит отдела%' AND lower(name) NOT LIKE '%руководитель it отдела%' AND lower(name) NOT LIKE '%начальник ит отдела%' AND lower(name) NOT LIKE '%руководитель отдела информационных технологий%' AND archived=0", (today,)).fetchone()['c']
    cnt_yest = conn.execute("SELECT COUNT(*) as c FROM vacancies WHERE published_date=? AND (lower(name) LIKE '%поддержк%' OR lower(name) LIKE '%support%' OR lower(name) LIKE '%service desk%' OR lower(name) LIKE '%helpdesk%' OR lower(name) LIKE '%customer success%' OR lower(name) LIKE '%customer service%' OR lower(name) LIKE '%клиентского сервиса%' OR lower(name) LIKE '%itsm%') AND lower(name) NOT LIKE '%руководитель ит отдела%' AND lower(name) NOT LIKE '%руководитель it отдела%' AND lower(name) NOT LIKE '%начальник ит отдела%' AND lower(name) NOT LIKE '%руководитель отдела информационных технологий%' AND archived=0", (yesterday,)).fetchone()['c']

    week_sal = conn.execute("""
        SELECT salary_from, salary_to FROM vacancies
        WHERE published_date >= ? AND (lower(name) LIKE '%поддержк%' OR lower(name) LIKE '%support%' OR lower(name) LIKE '%service desk%' OR lower(name) LIKE '%helpdesk%' OR lower(name) LIKE '%customer success%' OR lower(name) LIKE '%customer service%' OR lower(name) LIKE '%клиентского сервиса%' OR lower(name) LIKE '%itsm%') AND lower(name) NOT LIKE '%руководитель ит отдела%' AND lower(name) NOT LIKE '%руководитель it отдела%' AND lower(name) NOT LIKE '%начальник ит отдела%' AND lower(name) NOT LIKE '%руководитель отдела информационных технологий%' AND archived=0 AND salary_currency IN ('RUB','RUR')
    """, (monday,)).fetchall()
    week_total = conn.execute("SELECT COUNT(*) as c FROM vacancies WHERE published_date>=? AND (lower(name) LIKE '%поддержк%' OR lower(name) LIKE '%support%' OR lower(name) LIKE '%service desk%' OR lower(name) LIKE '%helpdesk%' OR lower(name) LIKE '%customer success%' OR lower(name) LIKE '%customer service%' OR lower(name) LIKE '%клиентского сервиса%' OR lower(name) LIKE '%itsm%') AND lower(name) NOT LIKE '%руководитель ит отдела%' AND lower(name) NOT LIKE '%руководитель it отдела%' AND lower(name) NOT LIKE '%начальник ит отдела%' AND lower(name) NOT LIKE '%руководитель отдела информационных технологий%' AND archived=0", (monday,)).fetchone()['c']
    def _fill(lst):
        out, last = [], None
        for x in lst:
            if x is None: x = last
            else: last = x
            out.append(x)
        first = next((x for x in out if x is not None), None)
        return [x if x is not None else first for x in out]
    med_from_l = _fill(med_from_l)
    med_to_l = _fill(med_to_l)

    week_med_from = median([r['salary_from'] for r in week_sal])
    week_med_to = median([r['salary_to'] for r in week_sal])

    top_salaries = conn.execute("""
        SELECT name, employer_name, salary_from, salary_to, alternate_url, published_date,
               (SELECT GROUP_CONCAT(format_name, ' / ') FROM vacancy_formats f WHERE f.vacancy_id = vacancies.id) AS formats
        FROM vacancies WHERE published_date >= ? AND (lower(name) LIKE '%поддержк%' OR lower(name) LIKE '%support%' OR lower(name) LIKE '%service desk%' OR lower(name) LIKE '%helpdesk%' OR lower(name) LIKE '%customer success%' OR lower(name) LIKE '%customer service%' OR lower(name) LIKE '%клиентского сервиса%' OR lower(name) LIKE '%itsm%') AND lower(name) NOT LIKE '%руководитель ит отдела%' AND lower(name) NOT LIKE '%руководитель it отдела%' AND lower(name) NOT LIKE '%начальник ит отдела%' AND lower(name) NOT LIKE '%руководитель отдела информационных технологий%' AND archived=0 AND salary_to IS NOT NULL AND salary_currency IN ('RUB','RUR')
        ORDER BY salary_to DESC LIMIT 10
    """, (monday,)).fetchall()

    prev = conn.execute(
        "SELECT * FROM weekly_reports WHERE week_start = ?",
        ((now - timedelta(days=now.weekday() + 7)).date().isoformat(),)
    ).fetchone()
    prev_monday = (now - timedelta(days=now.weekday() + 7)).date().isoformat()
    prev_same_day = (now - timedelta(days=7)).date().isoformat()
    sd_rows = conn.execute(
        "SELECT salary_from, salary_to FROM vacancies WHERE published_date BETWEEN ? AND ? AND (lower(name) LIKE '%поддержк%' OR lower(name) LIKE '%support%' OR lower(name) LIKE '%service desk%' OR lower(name) LIKE '%helpdesk%' OR lower(name) LIKE '%customer success%' OR lower(name) LIKE '%customer service%' OR lower(name) LIKE '%клиентского сервиса%' OR lower(name) LIKE '%itsm%') AND lower(name) NOT LIKE '%руководитель ит отдела%' AND lower(name) NOT LIKE '%руководитель it отдела%' AND lower(name) NOT LIKE '%начальник ит отдела%' AND lower(name) NOT LIKE '%руководитель отдела информационных технологий%' AND archived=0 AND salary_currency IN ('RUB','RUR')",
        (prev_monday, prev_same_day)).fetchall()
    sd_total = conn.execute(
        "SELECT COUNT(*) FROM vacancies WHERE published_date BETWEEN ? AND ? AND (lower(name) LIKE '%поддержк%' OR lower(name) LIKE '%support%' OR lower(name) LIKE '%service desk%' OR lower(name) LIKE '%helpdesk%' OR lower(name) LIKE '%customer success%' OR lower(name) LIKE '%customer service%' OR lower(name) LIKE '%клиентского сервиса%' OR lower(name) LIKE '%itsm%') AND lower(name) NOT LIKE '%руководитель ит отдела%' AND lower(name) NOT LIKE '%руководитель it отдела%' AND lower(name) NOT LIKE '%начальник ит отдела%' AND lower(name) NOT LIKE '%руководитель отдела информационных технологий%' AND archived=0",
        (prev_monday, prev_same_day)).fetchone()[0]
    def _med(vals):
        vals = sorted(v for v in vals if v is not None)
        if not vals: return None
        n = len(vals); m = n // 2
        return vals[m] if n % 2 else round((vals[m-1] + vals[m]) / 2)
    sd_from = _med([r['salary_from'] for r in sd_rows])
    sd_to = _med([r['salary_to'] for r in sd_rows])
    weekend_vacs = conn.execute(
        "SELECT name, employer_name, salary_from, salary_to, alternate_url, published_date "
        "FROM vacancies WHERE archived=0 AND strftime('%w', published_date) IN ('0','6') "
        "AND published_date >= ? AND (lower(name) LIKE '%поддержк%' OR lower(name) LIKE '%support%' OR lower(name) LIKE '%service desk%' OR lower(name) LIKE '%helpdesk%' OR lower(name) LIKE '%customer success%' OR lower(name) LIKE '%customer service%' OR lower(name) LIKE '%клиентского сервиса%' OR lower(name) LIKE '%itsm%') AND lower(name) NOT LIKE '%руководитель ит отдела%' AND lower(name) NOT LIKE '%руководитель it отдела%' AND lower(name) NOT LIKE '%начальник ит отдела%' AND lower(name) NOT LIKE '%руководитель отдела информационных технологий%' ORDER BY published_date DESC", (cutoff,)).fetchall()
    weekend_list = [{'url': r['alternate_url'], 'name': r['name'], 'employer': r['employer_name'],
                     'from': r['salary_from'], 'to': r['salary_to'], 'date': r['published_date']}
                    for r in weekend_vacs]
    ithead_vacs = conn.execute(
        "SELECT name, employer_name, salary_from, salary_to, alternate_url, published_date "
        "FROM vacancies WHERE published_date >= ? "
        "AND (lower(name) LIKE '%руководитель ит отдела%' OR lower(name) LIKE '%руководитель it отдела%' "
        "OR lower(name) LIKE '%начальник ит отдела%' OR lower(name) LIKE '%руководитель отдела информационных технологий%' "
        "OR lower(name) LIKE '%cto%' OR lower(name) LIKE '%cio%' OR lower(name) LIKE '%технический директор%' "
        "OR lower(name) LIKE '%ит-директор%' OR lower(name) LIKE '%ит директор%' OR lower(name) LIKE '%директор по информационным%' "
        "OR lower(name) LIKE '%директор по цифровой%' OR lower(name) LIKE '%руководитель ит-инфраструктуры%' OR lower(name) LIKE '%head of it%') "
        "ORDER BY published_date DESC", (cutoff,)).fetchall()
    ithead_list = [{'url': r['alternate_url'], 'name': r['name'], 'employer': r['employer_name'],
                    'from': r['salary_from'], 'to': r['salary_to'], 'date': r['published_date']}
                   for r in ithead_vacs]
    weekly = {
        'week_start': monday,
        'week_end': (now - timedelta(days=now.weekday()) + timedelta(days=4)).date().isoformat(),
        'total': week_total,
        'med_from': week_med_from,
        'med_to': week_med_to,
        'growth_total': pct(week_total, prev['total_vacancies']) if prev else None,
        'growth_from': pct(week_med_from, prev['med_salary_from']) if prev else None,
        'growth_to': pct(week_med_to, prev['med_salary_to']) if prev else None,
        'prev_total': prev['total_vacancies'] if prev else None,
        'prev_from': prev['med_salary_from'] if prev else None,
        'prev_to': prev['med_salary_to'] if prev else None,
        'sd_total': sd_total,
        'sd_from': sd_from,
        'sd_to': sd_to,
        'growth_total_sd': pct(week_total, sd_total) if sd_total else None,
        'growth_from_sd': pct(week_med_from, sd_from) if sd_from else None,
        'growth_to_sd': pct(week_med_to, sd_to) if sd_to else None,
        'weekend': weekend_list,
        'ithead': ithead_list,
    }

    top = conn.execute("""
        SELECT employer_name, COUNT(*) as c FROM vacancies
        WHERE published_date >= ? AND (lower(name) LIKE '%поддержк%' OR lower(name) LIKE '%support%' OR lower(name) LIKE '%service desk%' OR lower(name) LIKE '%helpdesk%' OR lower(name) LIKE '%customer success%' OR lower(name) LIKE '%customer service%' OR lower(name) LIKE '%клиентского сервиса%' OR lower(name) LIKE '%itsm%') AND lower(name) NOT LIKE '%руководитель ит отдела%' AND lower(name) NOT LIKE '%руководитель it отдела%' AND lower(name) NOT LIKE '%начальник ит отдела%' AND lower(name) NOT LIKE '%руководитель отдела информационных технологий%' AND archived=0 AND employer_name IS NOT NULL
        GROUP BY employer_name ORDER BY c DESC LIMIT 5
    """, (monday,)).fetchall()

    archived_week = conn.execute("""
        SELECT name, employer_name, salary_from, salary_to, alternate_url, published_date
        FROM vacancies WHERE archived=1 AND published_date >= ? AND (lower(name) LIKE '%поддержк%' OR lower(name) LIKE '%support%' OR lower(name) LIKE '%service desk%' OR lower(name) LIKE '%helpdesk%' OR lower(name) LIKE '%customer success%' OR lower(name) LIKE '%customer service%' OR lower(name) LIKE '%клиентского сервиса%' OR lower(name) LIKE '%itsm%') AND lower(name) NOT LIKE '%руководитель ит отдела%' AND lower(name) NOT LIKE '%руководитель it отдела%' AND lower(name) NOT LIKE '%начальник ит отдела%' AND lower(name) NOT LIKE '%руководитель отдела информационных технологий%'
        ORDER BY published_date DESC
    """, (monday,)).fetchall()
    archived_count = len(archived_week)
    total_week = conn.execute("""
        SELECT COUNT(*) FROM vacancies WHERE published_date >= ? AND (lower(name) LIKE '%поддержк%' OR lower(name) LIKE '%support%' OR lower(name) LIKE '%service desk%' OR lower(name) LIKE '%helpdesk%' OR lower(name) LIKE '%customer success%' OR lower(name) LIKE '%customer service%' OR lower(name) LIKE '%клиентского сервиса%' OR lower(name) LIKE '%itsm%') AND lower(name) NOT LIKE '%руководитель ит отдела%' AND lower(name) NOT LIKE '%руководитель it отдела%' AND lower(name) NOT LIKE '%начальник ит отдела%' AND lower(name) NOT LIKE '%руководитель отдела информационных технологий%'
    """, (monday,)).fetchone()[0]
    archived_pct = round(archived_count / total_week * 100, 1) if total_week > 0 else 0

    top_skills = conn.execute("""
        SELECT s.skill_name AS name, COUNT(*) AS c
        FROM vacancy_skills s JOIN vacancies v ON v.id = s.vacancy_id
        WHERE v.published_date >= ? AND (lower(name) LIKE '%поддержк%' OR lower(name) LIKE '%support%' OR lower(name) LIKE '%service desk%' OR lower(name) LIKE '%helpdesk%' OR lower(name) LIKE '%customer success%' OR lower(name) LIKE '%customer service%' OR lower(name) LIKE '%клиентского сервиса%' OR lower(name) LIKE '%itsm%') AND lower(name) NOT LIKE '%руководитель ит отдела%' AND lower(name) NOT LIKE '%руководитель it отдела%' AND lower(name) NOT LIKE '%начальник ит отдела%' AND lower(name) NOT LIKE '%руководитель отдела информационных технологий%' AND v.archived=0
        GROUP BY s.skill_name ORDER BY c DESC, s.skill_name
    """, (monday,)).fetchall()

    today_list = conn.execute("""
        SELECT name, employer_name, salary_from, salary_to, alternate_url,
               (SELECT GROUP_CONCAT(format_name, ' / ') FROM vacancy_formats f WHERE f.vacancy_id = vacancies.id) AS formats
        FROM vacancies WHERE published_date = ? AND (lower(name) LIKE '%поддержк%' OR lower(name) LIKE '%support%' OR lower(name) LIKE '%service desk%' OR lower(name) LIKE '%helpdesk%' OR lower(name) LIKE '%customer success%' OR lower(name) LIKE '%customer service%' OR lower(name) LIKE '%клиентского сервиса%' OR lower(name) LIKE '%itsm%') AND lower(name) NOT LIKE '%руководитель ит отдела%' AND lower(name) NOT LIKE '%руководитель it отдела%' AND lower(name) NOT LIKE '%начальник ит отдела%' AND lower(name) NOT LIKE '%руководитель отдела информационных технологий%' AND archived=0 ORDER BY first_seen_at DESC
    """, (today,)).fetchall()

    week_list = conn.execute("""
        SELECT name, employer_name, salary_from, salary_to, alternate_url, published_date,
               (SELECT GROUP_CONCAT(format_name, ' / ') FROM vacancy_formats f WHERE f.vacancy_id = vacancies.id) AS formats,
               (SELECT GROUP_CONCAT(skill_name, ', ') FROM vacancy_skills sk WHERE sk.vacancy_id = vacancies.id) AS skills, experience_name
        FROM vacancies WHERE published_date >= ? AND (lower(name) LIKE '%поддержк%' OR lower(name) LIKE '%support%' OR lower(name) LIKE '%service desk%' OR lower(name) LIKE '%helpdesk%' OR lower(name) LIKE '%customer success%' OR lower(name) LIKE '%customer service%' OR lower(name) LIKE '%клиентского сервиса%' OR lower(name) LIKE '%itsm%') AND lower(name) NOT LIKE '%руководитель ит отдела%' AND lower(name) NOT LIKE '%руководитель it отдела%' AND lower(name) NOT LIKE '%начальник ит отдела%' AND lower(name) NOT LIKE '%руководитель отдела информационных технологий%' AND archived=0
        ORDER BY published_date DESC, first_seen_at DESC LIMIT 200
    """, (monday,)).fetchall()

    conn.close()

    return jsonify({
        'labels': labels, 'counts': counts, 'avg_from': med_from_l, 'avg_to': med_to_l,
        'kpi': {'new_today': new_today, 'day_growth': pct(new_today, cnt_yest),
                'week_total': week_total, 'week_avg_from': week_med_from, 'week_avg_to': week_med_to},
        'weekly': weekly,
        'top': [{'name': r['employer_name'], 'count': r['c']} for r in top],
        'top_salaries': [{'name': r['name'], 'employer': r['employer_name'], 'from': r['salary_from'],
                          'to': r['salary_to'], 'schedule': r['formats'] or '—', 'url': r['alternate_url'], 'date': r['published_date']} for r in top_salaries],
        'top_skills': [{'name': r['name'], 'count': r['c']} for r in top_skills],
        'archived_list': [{'name': r['name'], 'employer': r['employer_name'], 'from': r['salary_from'], 'to': r['salary_to'], 'url': r['alternate_url'], 'date': r['published_date']} for r in archived_week],
        'archived_count': archived_count,
        'archived_pct': archived_pct,
        'today_list': [{'name': r['name'], 'employer': r['employer_name'], 'from': r['salary_from'],
                        'to': r['salary_to'], 'schedule': r['formats'] or '—', 'url': r['alternate_url']} for r in today_list],
        'week_list': [{'name': r['name'], 'employer': r['employer_name'], 'from': r['salary_from'],
                       'to': r['salary_to'], 'schedule': r['formats'] or '—', 'skills': r['skills'], 'experience': r['experience_name'], 'url': r['alternate_url'], 'date': r['published_date']} for r in week_list],
    })

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5001, debug=False)
