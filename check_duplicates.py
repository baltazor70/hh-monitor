"""Проверка дубликатов вакансий через hh API.
   Для каждого работодателя с дублями в БД запрашивает его активные вакансии
   и показывает кластеры одинаковых ролей."""
import sqlite3
from collections import defaultdict
from token_manager import get_cached_token
import httpx, os
from dotenv import load_dotenv

load_dotenv()
HEADERS = {"User-Agent": os.getenv("HH_USER_AGENT")}

def get_employer_vacancies(token, employer_id, page=0):
    """Все активные вакансии работодателя через API."""
    resp = httpx.get(
        "https://api.hh.ru/vacancies",
        params={"employer_id": employer_id, "per_page": 100, "page": page},
        headers={**HEADERS, "Authorization": f"Bearer {token}"},
        timeout=30
    )
    if resp.status_code != 200:
        return []
    return resp.json().get("items", [])

def main():
    conn = sqlite3.connect('hh_monitor.db')
    conn.row_factory = sqlite3.Row
    
    # Берём топ-20 работодателей по числу вакансий
    rows = conn.execute("""
        SELECT employer_id, employer_name, COUNT(*) cnt
        FROM vacancies
        WHERE archived=0 AND skip_reason IS NULL AND employer_id IS NOT NULL
        GROUP BY employer_id
        HAVING cnt >= 3
        ORDER BY cnt DESC LIMIT 20
    """).fetchall()
    
    token = get_cached_token()
    if not token:
        print("Не удалось получить токен")
        return
    
    print(f"Проверка {len(rows)} работодателей на дубли через API...\n")
    
    for row in rows:
        emp_id, emp_name = row["employer_id"], row["employer_name"]
        all_vacancies = []
        page = 0
        while page < 5:  # максимум 500 вакансий
            items = get_employer_vacancies(token, emp_id, page)
            if not items:
                break
            all_vacancies.extend(items)
            if len(items) < 100:
                break
            page += 1
        
        # Группируем по имени (case-insensitive)
        by_name = defaultdict(list)
        for v in all_vacancies:
            by_name[v["name"].lower()].append(v)
        
        # Находим кластеры дублей (2+ одинаковых имен)
        dups = {k: v for k, v in by_name.items() if len(v) > 1}
        if dups:
            print(f"=== {emp_name} (всего активных: {len(all_vacancies)}, дублей: {sum(len(v)-1 for v in dups.values())}) ===")
            for name, cluster in sorted(dups.items(), key=lambda x: -len(x[1]))[:5]:
                print(f"  [{len(cluster)}x] {cluster[0]['name']}")
                for v in cluster:
                    sal = v.get("salary") or {}
                    sal_str = f"{sal.get('from')}-{sal.get('to')} {sal.get('currency','')}" if sal.get('from') else "без вилки"
                    print(f"       id={v['id']}  {sal_str}  {v['published_at'][:10]}")
            print()

if __name__ == "__main__":
    main()
