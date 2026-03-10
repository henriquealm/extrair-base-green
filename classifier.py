import json

# ──────────────────────────────────────────
# Ajuste essas listas conforme a árvore de
# categorias real da Green by Missako
# ──────────────────────────────────────────

BOY_CATEGORIES = {
    "Meninos", "Bebê Menino", "Bermuda", "Camiseta e Body",
    "Camiseta e Regata", "Camisa", "Short", "Blusão", "Jaqueta",
}

GIRL_CATEGORIES = {
    "Vestido", "Vestidos", "Saia e Short", "Moda Íntima - Menina",
    "Tiara e Faixa", "Top", "Biquini", "Maiô", "Saída de Praia",
    "Macacão e Jardineira", "Macacão", "Jardineira", "Blusa e Regata",
    "Acessórios de Cabelo", "Meninas",
}

NEUTRAL_CATEGORIES = {
    "Acessórios", "Almofada e Pelúcia", "Bolsa e Mochila", "Calça",
    "Calçados", "Casaco", "Casaco e Jaqueta", "Chapéu e Gorro",
    "Conjuntos", "Naninha e Manta", "Praia",
}


def _parse_md_categories(tag_field) -> set:
    """Extrai categorias do campo categoryPurchasedTag do Master Data."""
    if not tag_field:
        return set()
    if isinstance(tag_field, str):
        try:
            tag_field = json.loads(tag_field)
        except Exception:
            return set()
    scores = tag_field.get("Scores", {})
    return set(scores.keys())


def _get_all_categories(customer: dict) -> set:
    """Combina categorias do MD tag + OMS."""
    cats = _parse_md_categories(customer.get("categoryPurchasedTag"))
    oms  = set(customer.get("_oms_categories", []))
    return cats | oms


def classify_customer(customer: dict) -> dict:
    """
    Adiciona ao dict do cliente os campos:
      - segment:    'meninos' | 'meninas' | 'ambos' | 'neutro' | 'sem_compra'
      - all_categories: lista ordenada de todas as categorias identificadas
    """
    cats = _get_all_categories(customer)

    has_boy    = bool(cats & BOY_CATEGORIES)
    has_girl   = bool(cats & GIRL_CATEGORIES)
    has_neutral = bool(cats & NEUTRAL_CATEGORIES)

    if has_boy and has_girl:
        segment = "ambos"
    elif has_boy:
        segment = "meninos"
    elif has_girl:
        segment = "meninas"
    elif has_neutral:
        segment = "neutro"
    else:
        segment = "sem_compra"

    customer["segment"]        = segment
    customer["all_categories"] = ", ".join(sorted(cats)) if cats else ""
    return customer
