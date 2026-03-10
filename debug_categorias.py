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

url  = f"{BASE_URL}/api/oms/pvt/orders?page=1&per_page=3&f_status=invoiced"
resp = requests.get(url, headers=HEADERS, timeout=30)
order_ids = [o.get("orderId") for o in resp.json().get("list", [])]

for order_id in order_ids:
    url2  = f"{BASE_URL}/api/oms/pvt/orders/{order_id}"
    data  = requests.get(url2, headers=HEADERS, timeout=30).json()
    items = data.get("items") or []

    print(f"\n{'='*60}")
    print(f"Pedido: {order_id}")
    print(f"Email: {(data.get('clientProfileData') or {}).get('email')}")
    print(f"Total de itens: {len(items)}")

    for i, item in enumerate(items[:2]):
        print(f"\n  Item {i+1}: {item.get('name', '')[:80]}")
        print(f"  productCategories: {json.dumps(item.get('productCategories'), ensure_ascii=False)}")
        add = item.get("additionalInfo") or {}
        print(f"  additionalInfo.categories: {json.dumps(add.get('categories'), ensure_ascii=False)}")
        print(f"  Chaves do item: {list(item.keys())}")