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

url = f"{BASE_URL}/api/oms/pvt/orders?page=1&per_page=5&f_status=invoiced,handling,ready-for-handling&_sort=creationDate+ASC"
resp = requests.get(url, headers=HEADERS, timeout=30)
data = resp.json()
print("=== PEDIDOS MAIS ANTIGOS ===")
for o in data.get("list", []):
    print(f"  {o.get('orderId')} | {o.get('creationDate')}")

time.sleep(1)

url2 = f"{BASE_URL}/api/oms/pvt/orders?page=1&per_page=5&f_status=invoiced&f_creationDate=creationDate:%5B2024-01-01T00:00:00Z%20TO%202024-01-31T23:59:59Z%5D"
resp2 = requests.get(url2, headers=HEADERS, timeout=30)
data2 = resp2.json()
print("\n=== FILTRO JAN/2024 ===")
print(f"  status={resp2.status_code} | total={data2.get('paging',{}).get('total')} | pages={data2.get('paging',{}).get('pages')}")
for o in data2.get("list", []):
    print(f"  {o.get('orderId')} | {o.get('creationDate')}")