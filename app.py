import os
import sqlite3
from functools import wraps
from datetime import datetime, timedelta

import pytz
from flask import Flask, render_template, jsonify, request, Response
from dotenv import load_dotenv

load_dotenv('/opt/hh-monitor/.env')

DB_PATH = '/opt/hh-monitor/hh_monitor.db'
MSK = pytz.timezone('Europe/Moscow')

app = Flask(__name__)

DASH_USER = os.getenv('DASH_USER', 'anton')
DASH_PASSWORD = os.getenv('DASH_PASSWORD', 'changeme')


def auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not (auth.username == DASH_USER and auth.password == DASH_PASSWORD):
            return Response('Требуется пароль', 401,
                            {'WWW-Authenticate': 'Basic realm="HH Monitor"'})
        return f(*args, **kwargs)
    return decorated


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def pct(cur, prev):
    """Процент прироста, защищен от деления на ноль"""
    if cur is None or prev is None or prev == 0:
        return None
    return round((cur - prev) / prev * 100, 1)


@app.route('/')
@auth_required
def index():
    return render_template('dashboard.html')


@app.route('/api/stats')
@auth_required
def stats():
    conn = get_db()
    now = datetime.now(MSK)
    today = now.date().isoformat()
    yesterday = (now - timedelta(days=1)).date().isoformat()
    cutoff = (now - timedelta(days=7)).date().isoformat()
    monday = (now - timedelta(days=now.weekday())).date().isoformat()

    # Динамика по дням (7 дней): количество + средние зарплаты
    rows = conn.execute("""
        SELECT published_date as d,
               COUNT(*) as total,
               ROUND(AVG(CASE WHEN salary_currency IN ('RUB','RUR') THEN salary_from END)) as avg_from,
               ROUND(AVG(CASE WHEN salary_currency IN ('RUB','RUR') THEN salary_to END)) as avg_to
        FROM vacancies WHERE published_date >= ?
        GROUP BY published_date ORDER BY published_date
    """, (cutoff,)).fetchall()

    new_today = conn.execute(
        "SELECT COUNT(*) as c FROM vacancies WHERE published_date = ?", (today,)
    ).fetchone()['c']
    cnt_yesterday = conn.execute(
        "SELECT COUNT(*) as c FROM vacancies WHERE published_date = ?", (yesterday,)
    ).fetchone()['c']

    # Текущая неделя (с понедельника)
    week = conn.execute("""
        SELECT COUNT(*) as total,
               ROUND(AVG(CASE WHEN salary_currency IN ('RUB','RUR') THEN salary_from END)) as avg_from,
               ROUND(AVG(CASE WHEN salary_currency IN ('RUB','RUR') THEN salary_to END)) as avg_to
        FROM vacancies WHERE published_date >= ?
    """, (monday,)).fetchone()

    # Недельный блок (обновляется в пятницу): последние 2 отчета
    reports = conn.execute(
        "SELECT * FROM weekly_reports ORDER BY week_start DESC LIMIT 2"
    ).fetchall()

    weekly = None
    if reports:
        cur_r = reports[0]
        prev_r = reports[1] if len(reports) > 1 else None
        weekly = {
            'week_start': cur_r['week_start'],
            'week_end': cur_r['week_end'],
            'total': cur_r['total_vacancies'],
            'avg_from': cur_r['avg_salary_from'],
            'avg_to': cur_r['avg_salary_to'],
            'growth_total': pct(cur_r['total_vacancies'], prev_r['total_vacancies']) if prev_r else None,
            'growth_from': pct(cur_r['avg_salary_from'], prev_r['avg_salary_from']) if prev_r else None,
            'growth_to': pct(cur_r['avg_salary_to'], prev_r['avg_salary_to']) if prev_r else None,
        }

    top = conn.execute("""
        SELECT employer_name, COUNT(*) as c FROM vacancies
        WHERE published_date >= ? AND employer_name IS NOT NULL
        GROUP BY employer_name ORDER BY c DESC LIMIT 5
    """, (monday,)).fetchall()

    latest = conn.execute("""
        SELECT name, employer_name, salary_from, salary_to, alternate_url, published_date
        FROM vacancies ORDER BY published_date DESC, first_seen_at DESC LIMIT 10
    """).fetchall()

    conn.close()

    return jsonify({
        'labels': [r['d'] for r in rows],
        'counts': [r['total'] for r in rows],
        'avg_from': [r['avg_from'] for r in rows],
        'avg_to': [r['avg_to'] for r in rows],
        'kpi': {
            'new_today': new_today,
            'day_growth': pct(new_today, cnt_yesterday),
            'week_total': week['total'],
            'week_avg_from': week['avg_from'],
            'week_avg_to': week['avg_to'],
        },
        'weekly': weekly,
        'top': [{'name': r['employer_name'], 'count': r['c']} for r in top],
        'latest': [{
            'name': r['name'], 'employer': r['employer_name'],
            'from': r['salary_from'], 'to': r['salary_to'],
            'url': r['alternate_url'], 'date': r['published_date']
        } for r in latest],
    })


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5001, debug=False)
