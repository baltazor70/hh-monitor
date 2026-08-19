import httpx
import sqlite3
import os
import json
import time
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv
from database import get_db, MSK

load_dotenv()

BASE_URL = "https://api.hh.ru"
HH_USER_AGENT = os.getenv("HH_USER_AGENT")

HEADERS = {
    "User-Agent": HH_USER_AGENT,
}

ROLE_GROUPS = {
    "head_of_support": [
        '"руководитель технической поддержки"',
        '"руководитель отдела технической поддержки"',
        '"head of support"',
        '"head of it support"',
        '"it support manager"',
        '"service desk manager"',
        '"руководитель service desk"',
    ],
    "team_lead_support": [
        '"team lead support"',
        '"team lead service desk"',
        '"тимлид поддержки"',
        '"тимлид технической поддержки"',
        '"руководитель группы поддержки"',
    ]
}

SCOPES = {
    "moscow": {"area": "1"},
    "remote": {"schedule": "remote"}
}

def get_access_token():
    """Получает access_token с retry"""
    for attempt in range(3):
        try:
            response = httpx.post(
                f"{BASE_URL}/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": os.getenv("HH_CLIENT_ID"),
                    "client_secret": os.getenv("HH_CLIENT_SECRET"),
                },
                headers=HEADERS,
                timeout=30.0
            )
            
            if response.status_code == 200:
                return response.json()["access_token"]
            
            if response.status_code == 429:
                print(f"[{datetime.now(MSK)}] Rate limit on token, waiting 60s...")
                time.sleep(60)
                continue
            
            print(f"[{datetime.now(MSK)}] Token error: {response.status_code}")
            time.sleep(10)
            
        except Exception as e:
            print(f"[{datetime.now(MSK)}] Token exception: {e}")
            time.sleep(10)
    
    return None

def fetch_vacancies(token: str, text: str, scope: dict, page: int = 0):
    """Делает запрос к HH API с retry"""
    params = {
        "text": text,
        "per_page": 100,
        "page": page,
        "order_by": "publication_time",
    }
    params.update(scope)
    
    for attempt in range(3):
        try:
            response = httpx.get(
                f"{BASE_URL}/vacancies",
                params=params,
                headers={**HEADERS, "Authorization": f"Bearer {token}"},
                timeout=30.0
            )
            
            if response.status_code == 200:
                return response.json()
            
            if response.status_code == 429:
                print(f"[{datetime.now(MSK)}] Rate limit, waiting 60s...")
                time.sleep(60)
                continue
            
            print(f"[{datetime.now(MSK)}] Fetch error: {response.status_code}")
            time.sleep(10)
            
        except Exception as e:
            print(f"[{datetime.now(MSK)}] Fetch exception: {e}")
            time.sleep(10)
    
    return None

def to_msk_date(iso_dt: str) -> str:
    if not iso_dt:
        return datetime.now(MSK).date().isoformat()
    try:
        dt = datetime.fromisoformat(iso_dt.replace('Z', '+00:00'))
        return dt.astimezone(MSK).date().isoformat()
    except:
        return datetime.now(MSK).date().isoformat()

def save_vacancy(vacancy: dict, role_group: str, scope_name: str, query_phrase: str):
    conn = get_db()
    
    vacancy_id = vacancy['id']
    published_at = vacancy.get('published_at')
    published_date = to_msk_date(published_at)
    
    existing = conn.execute(
        "SELECT id FROM vacancies WHERE id = ?",
        (vacancy_id,)
    ).fetchone()
    
    salary = vacancy.get('salary') or {}
    
    if not existing:
        conn.execute("""
            INSERT INTO vacancies (
                id, name, employer_id, employer_name, area_name,
                salary_from, salary_to, salary_currency, salary_gross,
                url, alternate_url, apply_alternate_url,
                published_at, published_date, first_seen_at, last_seen_at, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            vacancy_id,
            vacancy.get('name'),
            vacancy.get('employer', {}).get('id'),
            vacancy.get('employer', {}).get('name'),
            vacancy.get('area', {}).get('name'),
            salary.get('from'),
            salary.get('to'),
            salary.get('currency'),
            salary.get('gross'),
            vacancy.get('url'),
            vacancy.get('alternate_url'),
            vacancy.get('apply_alternate_url'),
            published_at,
            published_date,
            datetime.now(MSK).isoformat(),
            datetime.now(MSK).isoformat(),
            json.dumps(vacancy, ensure_ascii=False)
        ))
        print(f"[{datetime.now(MSK)}] Added: {vacancy.get('name')}")
    else:
        conn.execute(
            "UPDATE vacancies SET last_seen_at = ? WHERE id = ?",
            (datetime.now(MSK).isoformat(), vacancy_id)
        )
    
    conn.execute("""
        INSERT OR IGNORE INTO vacancy_matches (
            vacancy_id, role_group, search_scope, query_phrase, first_seen_at
        ) VALUES (?, ?, ?, ?, ?)
    """, (
        vacancy_id,
        role_group,
        scope_name,
        query_phrase,
        datetime.now(MSK).isoformat()
    ))
    
    conn.commit()
    conn.close()

def collect_vacancies():
    print(f"[{datetime.now(MSK)}] Starting vacancy collection...")
    
    token = get_access_token()
    if not token:
        print("Failed to get token after 3 attempts")
        return
    
    total_added = 0
    
    for role_group, phrases in ROLE_GROUPS.items():
        print(f"\n[{datetime.now(MSK)}] Processing: {role_group}")
        
        for phrase in phrases:
            print(f"  Searching: {phrase}")
            
            for scope_name, scope_params in SCOPES.items():
                page = 0
                while page < 3:
                    data = fetch_vacancies(token, phrase, scope_params, page)
                    
                    if not data:
                        break
                    
                    items = data.get('items', [])
                    
                    if not items:
                        break
                    
                    for vacancy in items:
                        save_vacancy(vacancy, role_group, scope_name, phrase)
                        total_added += 1
                    
                    if page >= data.get('pages', 1) - 1:
                        break
                    
                    page += 1
                    time.sleep(3)
    
    print(f"\n[{datetime.now(MSK)}] Collection completed. Total: {total_added}")

if __name__ == '__main__':
    collect_vacancies()
