import sqlite3
import os
from datetime import datetime
import pytz

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hh_monitor.db')
MSK = pytz.timezone('Europe/Moscow')

def get_db():
    """Подключение к базе данных"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Инициализация базы данных и создание таблиц"""
    conn = get_db()
    
    conn.executescript('''
        -- Таблица вакансий
        CREATE TABLE IF NOT EXISTS vacancies (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            employer_id TEXT,
            employer_name TEXT,
            area_name TEXT,
            salary_from INTEGER,
            salary_to INTEGER,
            salary_currency TEXT,
            salary_gross BOOLEAN,
            url TEXT,
            alternate_url TEXT,
            apply_alternate_url TEXT,
            published_at TEXT NOT NULL,
            published_date DATE NOT NULL,
            first_seen_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL,
            raw_json TEXT
        );

        -- Таблица совпадений (какая вакансия подошла под какой запрос)
        CREATE TABLE IF NOT EXISTS vacancy_matches (
            vacancy_id TEXT,
            role_group TEXT,
            search_scope TEXT,
            query_phrase TEXT,
            first_seen_at TEXT,
            PRIMARY KEY (vacancy_id, role_group, search_scope, query_phrase),
            FOREIGN KEY (vacancy_id) REFERENCES vacancies(id)
        );

        -- Таблица событий резюме (обновления, ошибки)
        CREATE TABLE IF NOT EXISTS resume_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            status TEXT NOT NULL,
            details TEXT,
            created_at TEXT NOT NULL
        );

        -- Таблица еженедельных отчетов
        CREATE TABLE IF NOT EXISTS weekly_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            week_start DATE NOT NULL,
            week_end DATE NOT NULL,
            total_vacancies INTEGER,
            avg_salary_from INTEGER,
            avg_salary_to INTEGER,
            top_companies TEXT,
            created_at TEXT NOT NULL
        );

        -- Индексы для ускорения запросов
        CREATE INDEX IF NOT EXISTS idx_vacancies_published_date 
            ON vacancies(published_date);
        
        CREATE INDEX IF NOT EXISTS idx_vacancy_matches_vacancy_id 
            ON vacancy_matches(vacancy_id);
    ''')
    
    conn.commit()
    conn.close()
    print(f"[{datetime.now(MSK)}] Database initialized successfully")

if __name__ == '__main__':
    init_db()
