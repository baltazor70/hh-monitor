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
        FROM vacancies WHERE published_date >= ?
        GROUP BY published_date
    """, (cutoff,)).fetchall()
    counts_by = {r['d']: r['total'] for r in counts_rows}

    sal_rows = conn.execute("""
        SELECT published_date as d, salary_from, salary_to FROM vacancies
        WHERE published_date >= ? AND salary_currency IN ('RUB','RUR')
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

    new_today = conn.execute("SELECT COUNT(*) as c FROM vacancies WHERE published_date=?", (today,)).fetchone()['c']
    cnt_yest = conn.execute("SELECT COUNT(*) as c FROM vacancies WHERE published_date=?", (yesterday,)).fetchone()['c']

    week_sal = conn.execute("""
        SELECT salary_from, salary_to FROM vacancies
        WHERE published_date >= ? AND salary_currency IN ('RUB','RUR')
    """, (monday,)).fetchall()
    week_total = conn.execute("SELECT COUNT(*) as c FROM vacancies WHERE published_date>=?", (monday,)).fetchone()['c']
    week_med_from = median([r['salary_from'] for r in week_sal])
    week_med_to = median([r['salary_to'] for r in week_sal])

    top_salaries = conn.execute("""
        SELECT name, employer_name, salary_from, salary_to, alternate_url, published_date
        FROM vacancies WHERE published_date >= ? AND salary_to IS NOT NULL AND salary_currency IN ('RUB','RUR')
        ORDER BY salary_to DESC LIMIT 10
    """, (monday,)).fetchall()

    experience_dist = conn.execute("""
        SELECT experience_name, COUNT(*) as c FROM vacancies
        WHERE published_date >= ? AND experience_name IS NOT NULL
        GROUP BY experience_name ORDER BY c DESC
    """, (monday,)).fetchall()

    reports = conn.execute("SELECT * FROM weekly_reports ORDER BY week_start DESC LIMIT 2").fetchall()
    weekly = None
    if reports:
        c, p = reports[0], (reports[1] if len(reports) > 1 else None)
        weekly = {
            'week_start': c['week_start'], 'week_end': c['week_end'], 'total': c['total_vacancies'],
            'med_from': c['med_salary_from'], 'med_to': c['med_salary_to'],
            'growth_total': pct(c['total_vacancies'], p['total_vacancies']) if p else None,
            'growth_from': pct(c['med_salary_from'], p['med_salary_from']) if p else None,
            'growth_to': pct(c['med_salary_to'], p['med_salary_to']) if p else None,
        }

    top = conn.execute("""
        SELECT employer_name, COUNT(*) as c FROM vacancies
        WHERE published_date >= ? AND employer_name IS NOT NULL
        GROUP BY employer_name ORDER BY c DESC LIMIT 5
    """, (monday,)).fetchall()

    latest = conn.execute("""
        SELECT name, employer_name, salary_from, salary_to, alternate_url, published_date
        FROM vacancies ORDER BY published_date DESC, first_seen_at DESC LIMIT 200
    """).fetchall()
    conn.close()

    return jsonify({
        'labels': labels, 'counts': counts, 'avg_from': med_from_l, 'avg_to': med_to_l,
        'kpi': {'new_today': new_today, 'day_growth': pct(new_today, cnt_yest),
                'week_total': week_total, 'week_avg_from': week_med_from, 'week_avg_to': week_med_to},
        'weekly': weekly,
        'top': [{'name': r['employer_name'], 'count': r['c']} for r in top],
        'top_salaries': [{'name': r['name'], 'employer': r['employer_name'], 'from': r['salary_from'],
                          'to': r['salary_to'], 'url': r['alternate_url'], 'date': r['published_date']} for r in top_salaries],
        'experience': [{'name': r['experience_name'], 'count': r['c']} for r in experience_dist],
        'latest': [{'name': r['name'], 'employer': r['employer_name'], 'from': r['salary_from'],
                    'to': r['salary_to'], 'url': r['alternate_url'], 'date': r['published_date']} for r in latest],
    })

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5001, debug=False)
