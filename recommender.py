# recommender.py
from __future__ import annotations
import ast
import pandas as pd
from typing import Dict, Any, List, Optional
from unicodedata import normalize as uni_normalize

# -------- Utils --------
def safe_list(x) -> List[str]:
    if isinstance(x, list):
        return x
    if isinstance(x, str):
        try:
            return ast.literal_eval(x)
        except Exception:
            return []
    return []

def slugify_tag(s: str) -> str:
    """
    Normaliza a TAG: mayúsculas, sin acentos, separadores -> underscore.
    """
    if not isinstance(s, str):
        return ""
    s = s.strip().upper()
    s = uni_normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    for ch in [" ", "-", ".", "/", ":", ";", ","]:
        s = s.replace(ch, "_")
    return s

def build_query_constraints(parsed_query: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convierte la query del usuario en tags estándar (CAT_*, INT_*, ATTR_*).
    """
    out = {"category_tag": None, "intent_tag": None, "attrs_tags": [], "brand": None}
    if parsed_query.get("categoria"):
        out["category_tag"] = f"CAT_{slugify_tag(parsed_query['categoria'])}"
    if parsed_query.get("intencion"):
        out["intent_tag"] = f"INT_{slugify_tag(parsed_query['intencion'])}"
    if parsed_query.get("marca"):
        out["brand"] = slugify_tag(parsed_query["marca"])
    if parsed_query.get("atributos"):
        out["attrs_tags"] = [f"ATTR_{slugify_tag(a)}" for a in parsed_query["atributos"]]
    return out

def prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Asegura columnas y tipos necesarios.
    Requiere: 'categoria_detectada', 'intencion_detectada', 'atributos_list' en df.
    """
    df = df.copy()
    # atributos_list puede venir como string -> lista
    if "atributos_list" in df.columns:
        df["atributos_list"] = df["atributos_list"].apply(safe_list)
    else:
        df["atributos_list"] = [[] for _ in range(len(df))]

    # Si tu pipeline usa 'atributos_correctos' como string con tags, podés mergearlo:
    # if "atributos_correctos" in df.columns and df["atributos_list"].eq([]).any():
    #     df["atributos_list"] = df["atributos_correctos"].apply(safe_list)

    # Normalizaciones defensivas
    for col in ("categoria_detectada", "intencion_detectada"):
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].fillna("")

    if "brand_name" not in df.columns:
        df["brand_name"] = ""

    return df

# -------- Core Ranking --------
def rank_products(
    model_scores: Dict[str, float],
    products_df: pd.DataFrame,
    parsed_query: Optional[Dict[str, Any]] = None,
    weights: Optional[Dict[str, float]] = None,
    top_k: int = 5,
    prefer_query_category: bool = True,
) -> pd.DataFrame:
    """
    Calcula un score por producto sumando:
      - score de categoría (CAT_*),
      - score de intención (INT_*),
      - score de atributos (ATTR_*),
    y aplica bonuses suaves guiados por la query del usuario.

    Parameters
    ----------
    model_scores: dict
        Salida del LLM {TAG: prob}
    products_df: pd.DataFrame
        Catálogo con columnas ['categoria_detectada','intencion_detectada','atributos_list', ...]
    parsed_query: dict | None
        {"categoria": "...", "intencion": "...", "marca": "...", "atributos": ["..."]}
    weights: dict | None
        Pesos para category/intent/attr. Ej: {"category":1.2,"intent":1.1,"attr":1.0}
    top_k: int
        Cantidad de ítems a devolver.
    prefer_query_category: bool
        Si True, prioriza la categoría pedida (si hay suficientes productos).

    Returns
    -------
    pd.DataFrame con columna 'similitud_total' y columnas clave del producto.
    """
    weights = weights or {"category": 1.0, "intent": 1.0, "attr": 1.0}
    df = prepare_dataframe(products_df)
    constraints = build_query_constraints(parsed_query or {})

    def score_row(row) -> float:
        score = 0.0

        # Categoria
        cat = row.get("categoria_detectada", "")
        if isinstance(cat, str) and cat in model_scores:
            score += model_scores[cat] * weights["category"]

        # Intencion
        intent = row.get("intencion_detectada", "")
        if isinstance(intent, str) and intent in model_scores:
            score += model_scores[intent] * weights["intent"]

        # Atributos
        attrs = row.get("atributos_list", [])
        for a in attrs:
            if a in model_scores:
                score += model_scores[a] * weights["attr"]

        # --- Bonuses suaves por constraints de la query ---
        # Marca exacta (no excluyente)
        if constraints["brand"]:
            brand_norm = slugify_tag(str(row.get("brand_name", "")))
            if constraints["brand"] == brand_norm:
                score += 0.25

        # Categoría/Intención pedidas explícitamente
        if constraints["category_tag"] and constraints["category_tag"] == cat:
            score += 0.15
        if constraints["intent_tag"] and constraints["intent_tag"] == intent:
            score += 0.15

        # Atributos requeridos en la query presentes en el producto
        if constraints["attrs_tags"]:
            inter = len(set(constraints["attrs_tags"]).intersection(set(attrs)))
            score += 0.05 * inter

        return score

    df = df.copy()
    df["similitud_total"] = df.apply(score_row, axis=1)

    # Preferencia por la categoría pedida (si hay suficientes resultados)
    if prefer_query_category and constraints["category_tag"]:
        sub = df[df["categoria_detectada"] == constraints["category_tag"]]
        if len(sub) >= top_k:
            df = sub

    cols_show = [
        "title",
        "brand_name",
        "categories",
        "list_price",
        "categoria_detectada",
        "intencion_detectada",
        "atributos_list",
        "similitud_total",
    ]
    cols_show = [c for c in cols_show if c in df.columns]  # por si faltan en el catálogo

    return (df.sort_values("similitud_total", ascending=False)
              .head(top_k)
              .loc[:, cols_show]
              .reset_index(drop=True))

# -------- Helper de alto nivel --------
def recommend_top_k_from_csv(
    csv_path: str,
    model_scores: Dict[str, float],
    parsed_query: Optional[Dict[str, Any]] = None,
    weights: Optional[Dict[str, float]] = None,
    top_k: int = 5,
    prefer_query_category: bool = True,
) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    return rank_products(
        model_scores=model_scores,
        products_df=df,
        parsed_query=parsed_query,
        weights=weights,
        top_k=top_k,
        prefer_query_category=prefer_query_category,
    )
