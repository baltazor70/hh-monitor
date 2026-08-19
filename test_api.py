import httpx, os
from dotenv import load_dotenv
load_dotenv()

UA = {"User-Agent": os.getenv("HH_USER_AGENT")}

# 1. Получаем токен приложения
r = httpx.post("https://api.hh.ru/token", data={
    "grant_type": "client_credentials",
    "client_id": os.getenv("HH_CLIENT_ID"),
    "client_secret": os.getenv("HH_CLIENT_SECRET"),
}, headers=UA, timeout=30)
print("TOKEN:", r.status_code)
if r.status_code != 200:
    print(r.text)
    raise SystemExit
token = r.json()["access_token"]

# 2. Пробуем поиск вакансий с токеном
r2 = httpx.get("https://api.hh.ru/vacancies", params={
    "text": "руководитель технической поддержки",
    "area": "1",
    "per_page": 5,
    "order_by": "publication_time",
}, headers={**UA, "Authorization": f"Bearer {token}"}, timeout=30)
print("SEARCH:", r2.status_code)
if r2.status_code == 200:
    data = r2.json()
    print("found:", data.get("found"))
    for item in data.get("items", [])[:5]:
        print("-", item["name"], "|", item.get("employer", {}).get("name"))
else:
    print(r2.text[:500])
