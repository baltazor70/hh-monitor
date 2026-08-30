import httpx
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
        '"руководитель департамента поддержки"',
        '"руководитель департамента технической поддержки"',
        '"руководитель службы технической поддержки"',
        '"руководитель службы поддержки"',
        '"руководитель службы 1 линии"',
        '"руководитель службы 2 линии"',
        '"руководитель мониторинга"',
        '"начальник отдела технической поддержки"',
        '"начальник службы поддержки"',
        '"начальник отдела поддержки"',
        '"руководитель поддержки L1"',
        '"руководитель поддержки L2"',
        '"руководитель L1"',
        '"руководитель L2"',
        '"head of L1"',
        '"head of L2"',
        '"head of line 1"',
        '"head of line 2"',
        '"head of first line"',
        '"head of second line"',
        '"руководитель сервиса поддержки"',
        '"руководитель сервиса технической поддержки"',
        '"начальник сервиса поддержки"',
        '"начальник сервиса технической поддержки"',
        '"head of service support"',
        '"service support manager"',
    ],
    "team_lead_support": [
        '"team lead support"',
        '"team lead service desk"',
        '"тимлид поддержки"',
        '"тимлид технической поддержки"',
        '"руководитель группы поддержки"',
        '"руководитель 1 линии поддержки"',
        '"руководитель 2 линии поддержки"',
        '"руководитель группы мониторинга"',
        '"тимлид 1 линии"',
        '"тимлид 2 линии"',
        '"team lead 1 line"',
        '"team lead 2 line"',
        '"тимлид L1"',
        '"тимлид L2"',
        '"тимлид поддержки L1"',
        '"тимлид поддержки L2"',
        '"team lead L1"',
        '"team lead L2"',
        '"teamlead L1"',
        '"teamlead L2"',
        '"team lead first line"',
        '"team lead second line"',
        '"teamlead first line"',
        '"teamlead second line"',
        '"тимлид сервиса поддержки"',
        '"тимлид сервиса технической поддержки"',
        '"team lead service support"',
        '"teamlead service support"',
    ],
    "it_head": [
        '"руководитель ИТ отдела"',
        '"руководитель it отдела"',
        '"начальник ИТ отдела"',
        '"head of it"',
        '"it manager"',
        '"руководитель отдела информационных технологий"',
    ]
}

ALLOWED_ROLES = {'121','113','105','104','189','114','112','116','36','125','40'}

SCOPES = {
    "moscow": {"area": "1"},
    "remote": {"schedule": "remote"}
}

TOKEN_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.token')

def get_access_token():
    try:
        with open(TOKEN_CACHE) as f:
            tok, exp = f.read().split()
        if time.time() < float(exp):
            return tok
    except Exception:
        pass
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
                j = response.json()
                try:
                    with open(TOKEN_CACHE, 'w') as f:
                        f.write("%s %s" % (j["access_token"], time.time() + min(float(j.get('expires_in', 43200)) - 60, 43200)))
                except Exception:
                    pass
                return j["access_token"]
            if response.status_code == 429:
                time.sleep(60); continue
            time.sleep(10)
        except Exception as e:
            print(f"[{datetime.now(MSK)}] Token exception: {e}")
            time.sleep(10)
    return None

def fetch_vacancies(token, text, scope, page=0):
    params = {"text": text, "per_page": 100, "page": page, "order_by": "publication_time"}
    params.update(scope)
    for attempt in range(3):
        try:
            response = httpx.get(
                f"{BASE_URL}/vacancies", params=params,
                headers={**HEADERS, "Authorization": f"Bearer {token}"}, timeout=30.0
            )
            if response.status_code == 200:
                return response.json()
            if response.status_code == 429:
                time.sleep(60); continue
            time.sleep(10)
        except Exception:
            time.sleep(10)
    return None

def fetch_vacancy_full(token, vacancy_id):
    try:
        response = httpx.get(
            f"{BASE_URL}/vacancies/{vacancy_id}",
            headers={**HEADERS, "Authorization": f"Bearer {token}"}, timeout=30.0
        )
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return None

def to_msk_date(iso_dt):
    if not iso_dt:
        return datetime.now(MSK).date().isoformat()
    try:
        dt = datetime.fromisoformat(iso_dt.replace('Z', '+00:00'))
        return dt.astimezone(MSK).date().isoformat()
    except Exception:
        return datetime.now(MSK).date().isoformat()

def is_relevant_role(vacancy):
    pro_role = vacancy.get('professional_roles', [])
    if not pro_role:
        return True
    return any(r.get('id') in ALLOWED_ROLES for r in pro_role)

MANAGER_MARKERS = ('руководитель','head of','lead','тимлид','teamlead','начальник','директор','director','manager','chief')
EXCLUDE_MARKERS = ('marketing','маркетинг','sales','продаж','разработки','developer','typescript','fullstack','frontend','backend','devops','cloud engineer','data ','hr','финанс','finance','юрист','legal','бухгалтер','логист','logist','закуп')

def is_manager_title(name):
    n = (name or '').lower()
    return any(m in n for m in MANAGER_MARKERS) and not any(e in n for e in EXCLUDE_MARKERS)

def save_vacancy(vacancy, role_group, scope_name, query_phrase, token):
    if not is_manager_title(vacancy.get('name')):
        return False
    if not is_relevant_role(vacancy):
        return 0

    conn = get_db()
    vacancy_id = vacancy['id']
    published_at = vacancy.get('published_at')
    published_date = to_msk_date(published_at)

    existing = conn.execute("SELECT id FROM vacancies WHERE id = ?", (vacancy_id,)).fetchone()

    salary = vacancy.get('salary') or {}
    experience = vacancy.get('experience') or {}
    pro_roles = vacancy.get('professional_roles', [])
    pro_role_id = pro_roles[0].get('id') if pro_roles else None

    schedule_id, schedule_name = None, None
    if not existing:
        full = fetch_vacancy_full(token, vacancy_id)
        wfs = []
        if full:
            wfs = full.get('work_format') or []
            if wfs:
                schedule_id, schedule_name = wfs[0].get('id'), wfs[0].get('name')
            time.sleep(1)

        conn.execute("""
            INSERT INTO vacancies (
                id, name, employer_id, employer_name, area_name,
                salary_from, salary_to, salary_currency, salary_gross,
                url, alternate_url, apply_alternate_url,
                published_at, published_date, first_seen_at, last_seen_at,
                experience_id, experience_name, professional_role_id,
                schedule_id, schedule_name, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            vacancy_id, vacancy.get('name'),
            vacancy.get('employer', {}).get('id'), vacancy.get('employer', {}).get('name'),
            vacancy.get('area', {}).get('name'),
            salary.get('from'), salary.get('to'), salary.get('currency'), salary.get('gross'),
            vacancy.get('url'), vacancy.get('alternate_url'), vacancy.get('apply_alternate_url'),
            published_at, published_date,
            datetime.now(MSK).isoformat(), datetime.now(MSK).isoformat(),
            experience.get('id'), experience.get('name'), pro_role_id,
            schedule_id, schedule_name,
            json.dumps(vacancy, ensure_ascii=False)
        ))
        for wf in wfs:
            conn.execute("""
                INSERT OR IGNORE INTO vacancy_formats (vacancy_id, format_id, format_name)
                VALUES (?, ?, ?)
            """, (vacancy_id, wf.get('id'), wf.get('name')))
        for sk in ((full.get('key_skills') or []) if full else []):
            conn.execute("""
                INSERT OR IGNORE INTO vacancy_skills (vacancy_id, skill_name)
                VALUES (?, ?)
            """, (vacancy_id, sk.get('name')))
        print(f"[{datetime.now(MSK)}] Added: {vacancy.get('name')} [{schedule_name or 'без формата'}]")
    else:
        conn.execute("""
            UPDATE vacancies SET last_seen_at = ?, experience_id = ?, experience_name = ?, professional_role_id = ?
            WHERE id = ?
        """, (datetime.now(MSK).isoformat(), experience.get('id'), experience.get('name'), pro_role_id, vacancy_id))

    conn.execute("""
        INSERT OR IGNORE INTO vacancy_matches (
            vacancy_id, role_group, search_scope, query_phrase, first_seen_at
        ) VALUES (?, ?, ?, ?, ?)
    """, (vacancy_id, role_group, scope_name, query_phrase, datetime.now(MSK).isoformat()))

    conn.commit()
    conn.close()
    return 1

def collect_vacancies():
    print(f"[{datetime.now(MSK)}] Starting vacancy collection...")
    token = get_access_token()
    if not token:
        print("Failed to get token after 3 attempts")
        return

    total_added = 0
    total_skipped = 0
    cutoff = (datetime.now(MSK) - timedelta(days=3)).date().isoformat()

    for role_group, phrases in ROLE_GROUPS.items():
        for phrase in phrases:
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
                        if save_vacancy(vacancy, role_group, scope_name, phrase, token):
                            total_added += 1
                        else:
                            total_skipped += 1
                    if to_msk_date(items[-1].get('published_at')) < cutoff:
                        break
                    if page >= data.get('pages', 1) - 1:
                        break
                    page += 1
                    time.sleep(3)

    print(f"[{datetime.now(MSK)}] Collection completed. Added: {total_added}, Skipped: {total_skipped}")

if __name__ == '__main__':
    collect_vacancies()
