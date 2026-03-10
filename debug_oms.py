import os, requests, time
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

for page in [1, 2, 29, 30, 31, 273]:
    url  = f"{BASE_URL}/api/oms/pvt/orders?page={page}&per_page=100&f_status=invoiced,handling,ready-for-handling"
    resp = requests.get(url, headers=HEADERS, timeout=30)
    data = resp.json()
    paging = data.get("paging", {})
    orders = data.get("list", [])
    print(f"Página {page:>3} | status={resp.status_code} | total={paging.get('total')} | pages={paging.get('pages')} | pedidos={len(orders)}")
    time.sleep(0.5)