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

# Verificar disponibilidad del modelo LLM
LLM_AVAILABLE = False
nlp_model = None

try:
    from es_ecommerce_classifier import load as load_model
    LLM_AVAILABLE = True
except (ImportError, OSError) as e:
    print(f"Modelo LLM no disponible: {e}")
    LLM_AVAILABLE = False

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="."), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Función para cargar datos reales del CSV
def load_data():
    """Carga los datos reales del CSV productos-gemini.csv"""
    try:
        df = pd.read_csv('datos/productos-gemini.csv')
        print(f"SUCCESS: Cargados {len(df)} productos del archivo CSV")
        print(f"Columnas disponibles: {list(df.columns)}")
        
        # Procesar la columna atributos_correctos para extraer categorías, intenciones y atributos
        df['parsed_attributes'] = df['atributos_correctos'].apply(parse_attributes)
        
        # Agregar campos separados para facilitar el cálculo de scores
        df['categoria_principal'] = df['parsed_attributes'].apply(lambda x: x.get('categoria', '') if x else '')
        df['intencion_principal'] = df['parsed_attributes'].apply(lambda x: x.get('intencion', '') if x else '')
        df['atributos_lista'] = df['parsed_attributes'].apply(lambda x: x.get('atributos', []) if x else [])
        
        # Agregar columnas que necesita el template (con valores por defecto)
        df['sale_price'] = df['list_price'] * 0.9  # Simular 10% descuento
        df['sku_id'] = df['slug']  # Usar slug como SKU
        df['discount_percent'] = 10.0  # Descuento fijo del 10%
        
        # Agregar columna de relevance_score inicializada en 0
        df['relevance_score'] = 0.0
        
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
    
    return df

# Cargar modelo LLM
def load_llm_model():
    if not LLM_AVAILABLE:
        return None

    try:
        model = load_model()
        return model
    except Exception as e:
        print(f"Error cargando el modelo LLM: {e}")
        return None

# Función para normalizar etiquetas del modelo (remover prefijos duplicados)
def normalize_labels(predictions: Dict[str, float]) -> Dict[str, float]:
    """
    Normaliza las etiquetas removiendo prefijos duplicados:
    - CAT_CAT_NOTEBOOK -> CAT_NOTEBOOK
    - INT_INT_GAMING -> INT_GAMING
    - ATTR_ATTR_TARJETA_GRAFICA -> ATTR_TARJETA_GRAFICA
    """
    normalized = {}
    
    for label, score in predictions.items():
        # Remover prefijos duplicados
        if label.startswith('CAT_CAT_'):
            clean_label = label.replace('CAT_CAT_', 'CAT_')
        elif label.startswith('INT_INT_'):
            clean_label = label.replace('INT_INT_', 'INT_')
        elif label.startswith('ATTR_ATTR_'):
            clean_label = label.replace('ATTR_ATTR_', 'ATTR_')
        else:
            clean_label = label
            
        normalized[clean_label] = score
    
    return normalized

# Función para predecir etiquetas de una consulta
def predict_labels(query: str, model) -> Dict[str, float]:
    if not model:
        return {}

    doc = model(query)
    predictions = {}

    # Obtener las predicciones del textcat_multilabel
    if hasattr(doc.cats, 'items'):
        raw_predictions = dict(doc.cats)
    else:
        # Fallback si la estructura es diferente
        raw_predictions = doc.cats

    # Normalizar las etiquetas removiendo prefijos duplicados
    normalized_predictions = normalize_labels(raw_predictions)
    
    return normalized_predictions

# Función para calcular score de un producto basado en texto (sin LLM)
def calculate_text_based_score(product: pd.Series, query: str) -> float:
    """Calcula score basado en coincidencia de texto cuando no hay modelo LLM"""
    score = 0.0
    query_lower = query.lower()
    title_lower = str(product.get('title', '')).lower()
    brand_lower = str(product.get('brand_name', '')).lower()
    
    # 1. Coincidencia exacta en título (peso alto)
    if query_lower in title_lower:
        score += 10.0
    
    # 2. Coincidencia parcial en título (peso medio)
    query_words = query_lower.split()
    for word in query_words:
        if len(word) > 2 and word in title_lower:  # Ignorar palabras muy cortas
            score += 3.0
    
    # 3. Coincidencia en marca
    if query_lower in brand_lower:
        score += 5.0
    
    # 4. Coincidencia en categoría
    categoria = str(product.get('categoria_principal', '')).lower()
    if query_lower in categoria:
        score += 4.0
    
    # 5. Coincidencia en intención
    intencion = str(product.get('intencion_principal', '')).lower()
    if query_lower in intencion:
        score += 3.0
    
    # 6. Coincidencia en atributos
    atributos = product.get('atributos_lista', [])
    if isinstance(atributos, list):
        for attr in atributos:
            if query_lower in str(attr).lower():
                score += 2.0
    
    return score

# Función para calcular score de un producto basado en las predicciones
def calculate_product_score(product: pd.Series, predictions: Dict[str, float]) -> float:
    score = 0.0
    
    # 1. Verificar categoría principal del producto
    categoria = product.get('categoria_principal', '')
    if categoria and categoria in predictions:
        score += predictions[categoria] * 5.0  # Mayor peso para categoría

    # 2. Verificar intención principal del producto
    intencion = product.get('intencion_principal', '')
    if intencion and intencion in predictions:
        score += predictions[intencion] * 4.0  # Alto peso para intención

    # 3. Verificar atributos del producto
    atributos = product.get('atributos_lista', [])
    if isinstance(atributos, list):
        for attr in atributos:
            if attr in predictions:
                score += predictions[attr] * 1.0  # Peso menor para atributos individuales

    # 4. Búsqueda por texto en el título (match adicional)
    title_lower = str(product.get('title', '')).lower()
    query_lower = str(predictions).lower()
    
    # Palabras clave para intenciones comunes
    if any(word in title_lower for word in ['gaming', 'gamer', 'juego', 'juegos']):
        if 'INT_GAMING' in predictions:
            score += predictions['INT_GAMING'] * 2.0

    if any(word in title_lower for word in ['oficina', 'trabajo', 'office', 'business']):
        if 'INT_OFICINA' in predictions:
            score += predictions['INT_OFICINA'] * 2.0

    if any(word in title_lower for word in ['estudio', 'estudiante', 'universidad']):
        if 'INT_ESTUDIO' in predictions:
            score += predictions['INT_ESTUDIO'] * 2.0

    if any(word in title_lower for word in ['diseño', 'diseñar', 'gráfico', 'creatividad']):
        if 'INT_DISEÑO' in predictions:
            score += predictions['INT_DISEÑO'] * 2.0

    return score

# Función de búsqueda inteligente
def intelligent_search(query: str, df: pd.DataFrame, model, top_k: int = 5) -> pd.DataFrame:
    if not query.strip():
        return df.head(top_k)

    # DEBUG: Mostrar información del dataset
    print(f"\n=== INICIO DE BÚSQUEDA ===")
    print(f"Query: '{query}'")
    print(f"Total productos disponibles: {len(df)}")
    print(f"Primer producto título: '{df.iloc[0]['title'] if len(df) > 0 else 'N/A'}'")
    
    # Si hay modelo LLM disponible, usarlo para predicciones inteligentes
    if model:
        predictions = predict_labels(query, model)
        
        # Mostrar salida del modelo en terminal como JSON
        print("\n=== SALIDA DEL MODELO LLM ===")
        print(f"Predicciones: {json.dumps(predictions, indent=2, ensure_ascii=False)}")
        print("=" * 40 + "\n")

        if predictions:
            # Calcular scores basados en predicciones del LLM
            scores = []
            for idx, product in df.iterrows():
                score = calculate_product_score(product, predictions)
                scores.append((idx, score))
        else:
            # Fallback a búsqueda por texto si no hay predicciones
            print("No hay predicciones del LLM, usando búsqueda por texto")
            scores = []
            for idx, product in df.iterrows():
                score = calculate_text_based_score(product, query)
                scores.append((idx, score))
    else:
        # Sin modelo LLM, usar búsqueda por texto en datos reales
        print(f"\n=== BÚSQUEDA POR TEXTO (LLM no disponible) ===")
        print(f"Buscando en {len(df)} productos del CSV...")
        
        scores = []
        for idx, product in df.iterrows():
            score = calculate_text_based_score(product, query)
            scores.append((idx, score))
            # DEBUG: Mostrar scores de productos relevantes
            if score > 0:
                print(f"  Producto: '{product['title'][:50]}...' - Score: {score:.2f}")

    # Ordenar por score descendente
    scores.sort(key=lambda x: x[1], reverse=True)

    # Tomar los top_k productos con mejor score
    top_indices = [idx for idx, score in scores[:top_k]]
    result_df = df.loc[top_indices].copy()

    # DEBUG: Mostrar resultados finales
    print(f"\n=== RESULTADOS FINALES ===")
    print(f"Productos seleccionados: {len(result_df)}")
    for i, (idx, score) in enumerate(scores[:top_k]):
        print(f"  {i+1}. Score {score:.2f}: '{df.loc[idx]['title'][:50]}...'")
    print("=" * 40 + "\n")

    # Agregar columna de score para mostrar
    result_df['relevance_score'] = [score for _, score in scores[:top_k]]

    return result_df

# Cargar datos y modelo
df = load_data()
llm_model = load_llm_model()

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index_moderno.html", {"request": request, "query": "", "filtered_df": None, "llm_available": llm_model is not None})

@app.post("/search", response_class=HTMLResponse)
async def search(request: Request, query: str = Form(...)):
    if query.strip():
        # Siempre intentar búsqueda inteligente (con o sin LLM)
        filtered_df = intelligent_search(query, df, llm_model, top_k=5)
        
        # DEBUG: Mostrar información sobre los resultados
        print(f"\nDEBUG: Query '{query}' - Resultados encontrados: {len(filtered_df)}")
        if len(filtered_df) > 0:
            print(f"DEBUG: Primer producto: {filtered_df.iloc[0].get('title', 'N/A')}")
            print(f"DEBUG: Total productos en dataset original: {len(df)}")
    else:
        filtered_df = df.head(10)  # Mostrar primeros 10 productos si no hay query

    return templates.TemplateResponse("index_moderno.html", {"request": request, "query": query, "filtered_df": filtered_df.to_dict('records') if filtered_df is not None else None, "llm_available": llm_model is not None})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)