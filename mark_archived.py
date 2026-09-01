import httpx, os, sqlite3, time
from dotenv import load_dotenv
load_dotenv('/opt/hh-monitor/.env')

from token_manager import get_cached_token
token = get_cached_token()
if not token:
    print("Failed to get token"); exit(1)
conn = sqlite3.connect('/opt/hh-monitor/hh_monitor.db')

rows = conn.execute("SELECT id FROM vacancies WHERE archived=0 AND published_date >= date('now','-21 day')").fetchall()
print(f"Проверка: {len(rows)}")
for r in rows:
    resp = httpx.get(f"https://api.hh.ru/vacancies/{r[0]}",
                     headers={'User-Agent': os.getenv('HH_USER_AGENT'), 'Authorization': f'Bearer {token}'},
                     timeout=30)
    if resp.status_code in (200, 404):
        dead = resp.status_code == 404 or resp.json().get('archived')
        if dead:
            conn.execute("UPDATE vacancies SET archived=1 WHERE id=?", (r[0],))
            conn.commit()
            print(f"  В архив: {r[0]}")
    time.sleep(1)

cur = conn.execute("DELETE FROM vacancies WHERE archived=1 AND published_date < date('now','-14 days')")
if cur.rowcount:
    conn.execute("DELETE FROM vacancy_skills WHERE vacancy_id NOT IN (SELECT id FROM vacancies)")
    conn.execute("DELETE FROM vacancy_formats WHERE vacancy_id NOT IN (SELECT id FROM vacancies)")
    conn.commit()
print(f"Удалено старых: {cur.rowcount}")
conn.close()
print("Готово")
