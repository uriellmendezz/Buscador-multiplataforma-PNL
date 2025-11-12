import pandas as pd
import os
from typing import List, Dict, Tuple
import numpy as np
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
import json
import ast
import re
from unicodedata import normalize as uni_normalize

# Verificar disponibilidad del modelo LLM
LLM_AVAILABLE = False
llm_model = None

try:
    from es_ecommerce_classifier import load as load_model
    # Intentar cargar el modelo
    try:
        llm_model = load_model()
        LLM_AVAILABLE = True
        print("SUCCESS: Modelo LLM cargado correctamente")
    except Exception as e:
        print(f"ERROR cargando modelo: {e}")
        LLM_AVAILABLE = False
except (ImportError, OSError) as e:
    print(f"Modelo LLM no disponible: {e}")
    LLM_AVAILABLE = False

def load_llm_model():
    """Carga el modelo LLM si está disponible"""
    global llm_model, LLM_AVAILABLE
    try:
        if not LLM_AVAILABLE:
            from es_ecommerce_classifier import load as load_model
            llm_model = load_model()
            LLM_AVAILABLE = True
        return llm_model
    except Exception as e:
        print(f"Error cargando modelo LLM: {e}")
        LLM_AVAILABLE = False
        return None

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="."), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# --- Helpers de normalización/parseo ---
def safe_list(x):
    """
    Convierte strings tipo "['ATTR_X','ATTR_Y']" a lista real.
    Si ya es lista, la devuelve; si falla, devuelve [].
    """
    if isinstance(x, list):
        return x
    if isinstance(x, str):
        try:
            return ast.literal_eval(x)
        except Exception:
            return []
    return []

def clean_label(label: str) -> str:
    """
    Normaliza labels del modelo:
    - Mayúsculas
    - Sin acentos
    - Espacios/guiones -> _
    - Colapsa prefijos duplicados (CAT_CAT_ -> CAT_, INT_INT_ -> INT_, ATTR_ATTR_ -> ATTR_)
    - Colapsa underscores repetidos
    """
    if not isinstance(label, str):
        label = str(label)
    s = label.strip().upper()
    s = uni_normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[ \-./:;,]+", "_", s)            # separadores -> _
    s = re.sub(r"^(CAT_)+", "CAT_", s)            # CAT_CAT_... -> CAT_
    s = re.sub(r"^(INT_)+", "INT_", s)            # INT_INT_... -> INT_
    s = re.sub(r"^(ATTR_)+", "ATTR_", s)          # ATTR_ATTR_... -> ATTR_
    s = re.sub(r"_+", "_", s)                     # varios __ -> _
    s = s.strip("_")
    return s

# Función para cargar datos reales del CSV
def load_data():
    """Carga los datos reales del CSV productos-gemini.csv"""
    try:
        # Intentar con diferentes rutas
        data_path = None
        possible_paths = ['datos/productos-gemini.csv', 'data/productos-gemini.csv', 'productos-gemini.csv']
        
        for path in possible_paths:
            if os.path.exists(path):
                data_path = path
                break
        
        if data_path is None:
            raise FileNotFoundError("No se encontró el archivo productos-gemini.csv en ninguna ubicación")
            
        df = pd.read_csv(data_path)
        print(f"SUCCESS: Cargados {len(df)} productos del archivo CSV: {data_path}")
        print(f"Columnas disponibles: {list(df.columns)}")
        
        # Procesar la columna atributos_correctos para extraer categorías, intenciones y atributos
        df['parsed_attributes'] = df['atributos_correctos'].apply(parse_attributes)
        
        # Agregar campos separados para facilitar el cálculo de scores
        df['categoria_principal'] = df['parsed_attributes'].apply(lambda x: x.get('categoria', '') if x else '')
        df['intencion_principal'] = df['parsed_attributes'].apply(lambda x: x.get('intencion', '') if x else '')
        df['atributos_lista'] = df['parsed_attributes'].apply(lambda x: x.get('atributos', []) if x else [])
        
        # Agregar columnas que necesita el template (con valores por defecto)
        if 'list_price' in df.columns:
            df['sale_price'] = df['list_price'] * 0.9  # Simular 10% descuento
        else:
            df['sale_price'] = 100000  # Precio por defecto
            
        df['sku_id'] = df['slug'] if 'slug' in df.columns else range(len(df))  # Usar slug como SKU
        df['discount_percent'] = 10.0  # Descuento fijo del 10%
        
        # Agregar columna de relevance_score inicializada en 0
        df['relevance_score'] = 0.0
        
        # Agregar columnas para compatibilidad con el sistema de tags
        if 'atributos_list' not in df.columns:
            df['atributos_list'] = df['atributos_lista'].apply(safe_list)
        if 'categoria_detectada' not in df.columns:
            df['categoria_detectada'] = df['categoria_principal']
        if 'intencion_detectada' not in df.columns:
            df['intencion_detectada'] = df['intencion_principal']
        
        print(f"SUCCESS: Datos procesados correctamente. Shape final: {df.shape}")
        return df
    except Exception as e:
        print(f"ERROR cargando datos del CSV: {e}")
        print("Usando datos de muestra como fallback")
        return load_sample_data()

def parse_attributes(attr_str):
    """Parsea la cadena JSON de atributos_correctos"""
    if pd.isna(attr_str) or not attr_str:
        return {}
    
    try:
        # Intentar parsear como diccionario
        if isinstance(attr_str, str):
            return ast.literal_eval(attr_str)
        return attr_str
    except Exception as e:
        print(f"Error parseando atributos: {e}")
        return {}

def load_sample_data():
    """Datos de muestra como fallback"""
    sample_data = {
        'title': ['Notebook Lenovo ThinkPad', 'Monitor Samsung', 'Auricular Sony'],
        'brand_name': ['Lenovo', 'Samsung', 'Sony'],
        'categories': ['CAT_NOTEBOOK', 'CAT_MONITOR', 'CAT_AURICULAR'],
        'list_price': [250000, 120000, 50000],
        'atributos_correctos': [
            {'categoria': 'CAT_NOTEBOOK', 'intencion': 'INT_OFICINA', 'atributos': ['ATTR_PORTATIL', 'ATTR_POTENTE']},
            {'categoria': 'CAT_MONITOR', 'intencion': 'INT_DISEÑO', 'atributos': ['ATTR_RESOLUCION_4K', 'ATTR_PANEL_IPS']},
            {'categoria': 'CAT_AURICULAR', 'intencion': 'INT_GAMING', 'atributos': ['ATTR_OVER_EAR', 'ATTR_BAJA_LATENCIA']}
        ]
    }
    
    df = pd.DataFrame(sample_data)
    df['parsed_attributes'] = df['atributos_correctos']
    df['categoria_principal'] = df['parsed_attributes'].apply(lambda x: x.get('categoria', '') if x else '')
    df['intencion_principal'] = df['parsed_attributes'].apply(lambda x: x.get('intencion', '') if x else '')
    df['atributos_lista'] = df['parsed_attributes'].apply(lambda x: x.get('atributos', []) if x else [])
    
    # Agregar columnas de compatibilidad
    df['atributos_list'] = df['atributos_lista'].apply(safe_list)
    df['categoria_detectada'] = df['categoria_principal']
    df['intencion_detectada'] = df['intencion_principal']
    df['slug'] = range(len(df))
    
    return df

# --- Similitud (conteo de coincidencias) ---
def similitud_producto(row: pd.Series, tags_set: set) -> int:
    """
    Suma:
      +1 si coincide categoria_detectada
      +1 si coincide intencion_detectada
      +1 por cada ATTR_* presente en atributos_list que esté en tags_set
    """
    total = 0
    cat = row.get("categoria_detectada", "")
    intent = row.get("intencion_detectada", "")
    attrs = row.get("atributos_list", [])

    if isinstance(cat, str) and cat in tags_set:
        total += 1
    if isinstance(intent, str) and intent in tags_set:
        total += 1
    if isinstance(attrs, list):
        total += len(set(attrs).intersection(tags_set))

    return total

# --- Generación de tags desde LLM o dict de scores ---
def generar_tags(query: str = "",
                 model=None,
                 scores_dict: dict | None = None,
                 topn: int = 15) -> list[str]:
    """
    Devuelve la lista ordenada de tags más probables.
    - Si pasás scores_dict (p.ej. salida ya parseada de tu LLM): usa eso.
    - Si pasás model (spacy/llm con doc.cats): usa model(query).
    - Si pasás ambos, prioriza scores_dict.
    """
    if scores_dict is not None:
        raw_predictions = scores_dict
    else:
        if model is None:
            raise ValueError("Debes pasar `scores_dict` o `model` para generar tags.")
        doc = model(query)
        raw_predictions = getattr(doc, "cats", {})

    # Normalizar labels
    cleaned_predictions = { clean_label(k): float(v) for k, v in raw_predictions.items() }

    # Ordenar por score desc
    predicciones_ordenadas = sorted(cleaned_predictions.items(), key=lambda x: x[1], reverse=True)
    tags = [k for k, _ in predicciones_ordenadas[:topn]]
    return tags

# --- Pipeline completo ---
def filtrar_por_tags(df: pd.DataFrame, tags: list[str], min_coincidencias: int = 2) -> pd.DataFrame:
    """
    Calcula similitud y devuelve DF filtrado (similitud >= min_coincidencias) y ordenado.
    """
    df = df.copy()

    # Asegurar columnas
    if "atributos_list" not in df.columns:
        df["atributos_list"] = [[] for _ in range(len(df))]
    else:
        df["atributos_list"] = df["atributos_list"].apply(safe_list)

    for col in ("categoria_detectada", "intencion_detectada"):
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].fillna("")

    # Preparar set de tags
    tags_norm = { clean_label(t) for t in tags if isinstance(t, str) and t.strip() }

    # Calcular similitud
    df["similitud"] = df.apply(lambda r: similitud_producto(r, tags_norm), axis=1)

    # Filtrar y ordenar
    df_filtrado = df[df["similitud"] >= min_coincidencias].sort_values("similitud", ascending=False)

    # Columnas útiles (ajusta según tu catálogo)
    cols_show = [c for c in [
        "title", "brand_name", "categories", "list_price",
        "categoria_detectada", "intencion_detectada", "atributos_list",
        "similitud"
    ] if c in df_filtrado.columns]

    return df_filtrado.loc[:, cols_show]

def intelligent_search(query: str, df: pd.DataFrame, model=None, top_k: int = 5):
    """
    Realiza búsqueda inteligente usando el modelo LLM si está disponible,
    o búsqueda por texto si no está disponible.
    """
    try:
        if model is not None:
            # Usar modelo LLM para generar tags y filtrar
            tags = generar_tags(query, model=model)
            print(f"Tags generados para '{query}': {tags}")
            filtered_df = filtrar_por_tags(df, tags, min_coincidencias=0)  # Incluir más productos
        else:
            # Búsqueda simple por texto en título y marca
            query_lower = query.lower()
            if 'title' in df.columns and 'brand_name' in df.columns:
                mask = (df['title'].str.lower().str.contains(query_lower, na=False) | 
                       df['brand_name'].str.lower().str.contains(query_lower, na=False))
                filtered_df = df[mask].copy()
            else:
                filtered_df = df.copy()
                
        # Agregar relevance_score basado en similitud
        if 'similitud' in filtered_df.columns:
            filtered_df['relevance_score'] = filtered_df['similitud']
        else:
            filtered_df['relevance_score'] = 1.0
            
        # Ordenar por relevancia y retornar top_k
        filtered_df = filtered_df.sort_values('relevance_score', ascending=False).head(top_k)
        return filtered_df
        
    except Exception as e:
        print(f"Error en búsqueda inteligente: {e}")
        # Fallback a búsqueda simple
        query_lower = query.lower()
        mask = df['title'].str.lower().str.contains(query_lower, na=False) if 'title' in df.columns else pd.Series([True] * len(df))
        return df[mask].head(top_k)

# Cargar datos al inicio
try:
    df = load_data()
    # Cargar modelo si está disponible
    if LLM_AVAILABLE:
        llm_model = load_llm_model()
except Exception as e:
    print(f"Error inicializando datos: {e}")
    df = load_sample_data()

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index_moderno.html", {"request": request, "query": "", "filtered_df": None, "llm_available": LLM_AVAILABLE})

@app.post("/search", response_class=HTMLResponse)
async def search(request: Request, query: str = Form(...)):
    if query.strip():
        # Siempre intentar búsqueda inteligente (con o sin LLM)
        filtered_df = intelligent_search(query, df, llm_model, top_k=12)
        
        # DEBUG: Mostrar información sobre los resultados
        print(f"\nDEBUG: Query '{query}' - Resultados encontrados: {len(filtered_df)}")
        if len(filtered_df) > 0:
            print(f"DEBUG: Primer producto: {filtered_df.iloc[0].get('title', 'N/A')}")
            print(f"DEBUG: Total productos en dataset original: {len(df)}")
    else:
        filtered_df = df.head(12).copy()  # Mostrar 12 productos si no hay query
        # Agregar scores ficticios para mostrar todos con el mismo nivel
        filtered_df['relevance_score'] = 0.5
        filtered_df['similitud'] = 0

    return templates.TemplateResponse("index_moderno.html", {"request": request, "query": query, "filtered_df": filtered_df.to_dict('records') if filtered_df is not None and len(filtered_df) > 0 else None, "llm_available": LLM_AVAILABLE})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)