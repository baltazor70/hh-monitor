import sqlite3
import pytz

DB_PATH = '/opt/hh-monitor/hh_monitor.db'
MSK = pytz.timezone('Europe/Moscow')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS vacancies (
            id TEXT PRIMARY KEY,
            name TEXT,
            employer_id TEXT,
            employer_name TEXT,
            area_name TEXT,
            salary_from INTEGER,
            salary_to INTEGER,
            salary_currency TEXT,
            salary_gross INTEGER,
            url TEXT,
            alternate_url TEXT,
            apply_alternate_url TEXT,
            published_at TEXT,
            published_date TEXT,
            first_seen_at TEXT,
            last_seen_at TEXT,
            experience_id TEXT,
            experience_name TEXT,
            professional_role_id TEXT,
            raw_json TEXT
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS vacancy_matches (
            vacancy_id TEXT,
            role_group TEXT,
            search_scope TEXT,
            query_phrase TEXT,
            first_seen_at TEXT,
            PRIMARY KEY (vacancy_id, role_group, search_scope)
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS weekly_reports (
            week_start TEXT PRIMARY KEY,
            week_end TEXT,
            total_vacancies INTEGER,
            avg_salary_from INTEGER,
            avg_salary_to INTEGER,
            med_salary_from INTEGER,
            med_salary_to INTEGER,
            top_companies TEXT,
            created_at TEXT
        )
    """)
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print(f"[{__import__('datetime').datetime.now(MSK)}] Database initialized successfully")
