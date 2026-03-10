import os, requests, json
from dotenv import load_dotenv

load_dotenv()

ACCOUNT   = os.getenv("VTEX_ACCOUNT")
ENV       = os.getenv("VTEX_ENV", "vtexcommercestable")
APP_KEY   = os.getenv("VTEX_APP_KEY")
APP_TOKEN = os.getenv("VTEX_APP_TOKEN")
BASE_URL  = f"https://{ACCOUNT}.{ENV}.com.br"

HEADERS = {
    "X-VTEX-API-AppKey":   APP_KEY,
    "X-VTEX-API-AppToken": APP_TOKEN,
    "Content-Type":        "application/json",
}

# Testa entidade AP do Master Data
url  = f"{BASE_URL}/api/dataentities/AP/scroll?_fields=email,items,creationDate&_size=3"
resp = requests.get(url, headers=HEADERS, timeout=30)
print(f"Entidade AP — status: {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    print(json.dumps(data[:1], indent=2, ensure_ascii=False))