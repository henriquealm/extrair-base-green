import os
import time
import json
import pickle
import warnings
import requests
import pandas as pd
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dotenv import load_dotenv
from classifier import classify_customer
from exporter import export_to_excel

warnings.filterwarnings("ignore")
load_dotenv()

ACCOUNT   = os.getenv("VTEX_ACCOUNT")
ENV       = os.getenv("VTEX_ENV", "vtexcommercestable")
APP_KEY   = os.getenv("VTEX_APP_KEY")
APP_TOKEN = os.getenv("VTEX_APP_TOKEN")

BASE_URL        = f"https://{ACCOUNT}.{ENV}.com.br"
CACHE_CATS_FILE = "output/cache_email_cats.pkl"


# ──────────────────────────────────────────
# SESSION com retry automático
# ──────────────────────────────────────────
def make_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=5,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.headers.update({
        "X-VTEX-API-AppKey":   APP_KEY,
        "X-VTEX-API-AppToken": APP_TOKEN,
        "Content-Type":        "application/json",
    })
    return session


SESSION = make_session()


def safe_get(url: str, pause: float = 0.3) -> dict:
    try:
        resp = SESSION.get(url, timeout=30)
        if resp.status_code == 429:
            print("  ⏳ Rate limit — aguardando 15s...")
            time.sleep(15)
            return safe_get(url, pause)
        if resp.status_code not in (200, 206):
            return {}
        time.sleep(pause)
        return resp.json()
    except Exception as e:
        print(f"  ⚠️  Conexão perdida: {e} — aguardando 10s...")
        time.sleep(10)
        try:
            resp = SESSION.get(url, timeout=30)
            return resp.json() if resp.status_code == 200 else {}
        except Exception:
            return {}


def clean_email(email: str) -> str:
    """Remove sufixo .ct.vtex.com.br gerado em pedidos de call center."""
    email = (email or "").lower().strip()
    if ".ct.vtex.com.br" in email:
        email = email.split("-")[0]
    return email


# ──────────────────────────────────────────
# 1. MASTER DATA — base completa de clientes
# ──────────────────────────────────────────
def fetch_all_customers() -> list:
    print("🔄 Buscando clientes no Master Data (CL)...")
    fields = "email,firstName,lastName,categoryPurchasedTag,isNewsletterOptIn"
    url    = f"{BASE_URL}/api/dataentities/CL/scroll?_fields={fields}&_size=1000"

    customers = []
    token     = None

    while True:
        req_url = f"{url}&_token={token}" if token else url
        resp    = SESSION.get(req_url, timeout=30)

        if resp.status_code == 429:
            print("  ⏳ Rate limit — aguardando 5s...")
            time.sleep(5)
            continue

        resp.raise_for_status()
        token = resp.headers.get("X-VTEX-MD-TOKEN")
        batch = resp.json()

        if not batch:
            break

        customers.extend(batch)
        print(f"  ✅ {len(customers)} clientes carregados...")

        if not token:
            break

        time.sleep(0.3)

    print(f"\n📦 Total na base CL: {len(customers)}")
    return customers


# ──────────────────────────────────────────
# 2. OMS — paginação por âncora de data
#    Contorna o limite de 30 páginas usando
#    o creationDate do último pedido de cada
#    lote como âncora para o próximo lote
# ──────────────────────────────────────────
def extract_categories_from_items(items: list) -> set:
    cats = set()
    for item in (items or []):
        if not item:
            continue
        for cat_name in (item.get("productCategories") or {}).values():
            if cat_name:
                cats.add(cat_name)
        for cat in ((item.get("additionalInfo") or {}).get("categories") or []):
            name = (cat or {}).get("name", "")
            if name:
                cats.add(name)
    return cats


def fetch_email_categories_from_oms() -> dict:
    os.makedirs("output", exist_ok=True)

    if os.path.exists(CACHE_CATS_FILE):
        with open(CACHE_CATS_FILE, "rb") as f:
            cache = pickle.load(f)
        email_cats  = cache["email_cats"]
        anchor_date = cache["anchor_date"]
        total_proc  = cache["total_processed"]
        print(f"♻️  Retomando do cache: {total_proc} pedidos | âncora: {anchor_date}")
    else:
        email_cats  = {}
        anchor_date = None  # começa do mais recente
        total_proc  = 0

    print(f"\n🔄 Coletando pedidos do OMS por âncora de data...")

    batch_num  = 0
    per_page   = 100
    max_pages  = 29  # fica abaixo do limite de 30

    while True:
        batch_ids   = []
        oldest_date = None

        # coleta até max_pages páginas a partir da âncora
        for page in range(1, max_pages + 1):
            if anchor_date:
                url = (
                    f"{BASE_URL}/api/oms/pvt/orders"
                    f"?page={page}&per_page={per_page}"
                    f"&f_status=invoiced,handling,ready-for-handling"
                    f"&f_creationDate=creationDate:%5B1970-01-01T00:00:00Z%20TO%20{anchor_date}%5D"
                )
            else:
                url = (
                    f"{BASE_URL}/api/oms/pvt/orders"
                    f"?page={page}&per_page={per_page}"
                    f"&f_status=invoiced,handling,ready-for-handling"
                )

            data = safe_get(url, pause=0.3)
            if not data:
                break

            orders = data.get("list") or []
            if not orders:
                break

            for order in orders:
                oid  = (order or {}).get("orderId")
                date = (order or {}).get("creationDate", "")
                if oid:
                    batch_ids.append(oid)
                if date:
                    oldest_date = date

            total_pages = data.get("paging", {}).get("pages", 1)
            if page >= total_pages:
                # chegamos ao fim de todos os pedidos
                anchor_date = None
                break
        else:
            # saiu pelo range — ainda há mais pedidos
            # usa o mais antigo deste lote como nova âncora
            if oldest_date:
                # subtrai 1 segundo para não repetir o último pedido
                dt = datetime.fromisoformat(oldest_date.replace("Z", "+00:00").replace("+00:00", ""))
                anchor_date = (dt - __import__('datetime').timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%SZ")

        if not batch_ids:
            break

        # busca detalhe dos pedidos em paralelo (10 threads)
        from concurrent.futures import ThreadPoolExecutor, as_completed

        def fetch_detail(order_id):
            url = f"{BASE_URL}/api/oms/pvt/orders/{order_id}"
            return safe_get(url, pause=0.1)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(fetch_detail, oid): oid for oid in batch_ids}
            for future in as_completed(futures):
                detail = future.result()
                if not detail:
                    continue

                email = clean_email(
                    (detail.get("clientProfileData") or {}).get("email", "")
                )
                if not email:
                    continue

                cats = extract_categories_from_items(detail.get("items") or [])
                if email not in email_cats:
                    email_cats[email] = set()
                email_cats[email] |= cats

        total_proc += len(batch_ids)
        batch_num  += 1

        print(f"  ✅ Lote {batch_num} — {total_proc} pedidos processados | {len(email_cats)} clientes mapeados")

        # salva cache após cada lote
        with open(CACHE_CATS_FILE, "wb") as f:
            pickle.dump({
                "email_cats":      email_cats,
                "anchor_date":     anchor_date,
                "total_processed": total_proc,
            }, f)

        if anchor_date is None:
            break

    if os.path.exists(CACHE_CATS_FILE):
        os.remove(CACHE_CATS_FILE)

    print(f"\n📬 Clientes com categorias identificadas: {len(email_cats)}")
    return email_cats


# ──────────────────────────────────────────
# 3. CRUZAMENTO — CL + categorias do OMS
# ──────────────────────────────────────────
def enrich_customers(customers: list, email_cats: dict) -> list:
    print(f"\n🔗 Cruzando {len(customers)} clientes com categorias do OMS...")

    for c in customers:
        email    = (c.get("email") or "").lower().strip()
        oms_cats = email_cats.get(email, set())

        c["_oms_categories"] = list(oms_cats)

        has_md = _has_md_tag(c)
        if has_md and oms_cats:
            c["_source"] = "MD_tag + OMS"
        elif has_md:
            c["_source"] = "MD_tag"
        elif oms_cats:
            c["_source"] = "OMS"
        else:
            c["_source"] = "sem_compra"

    tagged      = sum(1 for c in customers if c["_source"] != "sem_compra")
    no_purchase = len(customers) - tagged
    print(f"  ✅ Com compra: {tagged} | Sem compra: {no_purchase}")
    return customers


def _has_md_tag(customer: dict) -> bool:
    tag = customer.get("categoryPurchasedTag", {})
    if not tag:
        return False
    if isinstance(tag, str):
        try:
            tag = json.loads(tag)
        except Exception:
            return False
    return bool(tag.get("Scores", {}))


# ──────────────────────────────────────────
# 4. MAIN
# ──────────────────────────────────────────
if __name__ == "__main__":
    customers  = fetch_all_customers()
    email_cats = fetch_email_categories_from_oms()
    customers  = enrich_customers(customers, email_cats)

    for c in customers:
        first = (c.get("firstName") or "").strip()
        last  = (c.get("lastName")  or "").strip()
        c["fullName"] = f"{first} {last}".strip() or "—"
        classify_customer(c)

    os.makedirs("output", exist_ok=True)
    df = pd.DataFrame(customers)
    export_to_excel(df, "output/segmentacao_missako.xlsx")

    print("\n✅ Arquivo gerado em output/segmentacao_missako.xlsx")
