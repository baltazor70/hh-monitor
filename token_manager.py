"""Общий менеджер токена hh API. Кеширует токен в .token до истечения срока.
   Все скрипты (collector, mark_archived) получают один и тот же токен,
   hh не аннулирует его из-за повторных OAuth-запросов."""
import httpx, os, time
from dotenv import load_dotenv

load_dotenv()

TOKEN_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.token')
BASE_URL = "https://api.hh.ru"
HH_USER_AGENT = os.getenv("HH_USER_AGENT")
HEADERS = {"User-Agent": HH_USER_AGENT}

def get_cached_token():
    try:
        with open(TOKEN_CACHE) as f:
            tok, exp = f.read().split()
        if time.time() < float(exp) - 60:
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
                expires_in = float(j.get('expires_in', 43200))
                with open(TOKEN_CACHE, 'w') as f:
                    f.write(f"{j['access_token']} {time.time() + expires_in - 60}")
                return j['access_token']
            if response.status_code == 429:
                time.sleep(60); continue
            time.sleep(10)
        except Exception as e:
            print(f"Token exception: {e}")
            time.sleep(10)
    return None
