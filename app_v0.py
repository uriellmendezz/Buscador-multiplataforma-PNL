import pandas as pd
import os
from typing import List, Dict, Tuple
import numpy as np
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

# Verificar disponibilidad de spaCy
SPACY_AVAILABLE = False
spacy = None

try:
    import spacy
    SPACY_AVAILABLE = True
except (ImportError, OSError) as e:
    print(f"spaCy no disponible: {e}")
    SPACY_AVAILABLE = False

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="."), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Función para cargar datos
def load_data():
    # Intentar cargar datos reales si existen
    data_path = 'datos/lenovo/productos.csv'
    if os.path.exists(data_path):
        df = pd.read_csv(data_path)
        return df

    # Si no existen datos reales, crear datos de ejemplo
    sample_data = {
        'id': [1, 2, 3, 4, 5],
        'title': [
            'Notebook Lenovo ThinkPad X1 Carbon',
            'Notebook Lenovo IdeaPad 3',
            'Notebook Lenovo Yoga 7i',
            'PC Lenovo ThinkCentre M70q',
            'Monitor Lenovo ThinkVision T24i'
        ],
        'brand_name': ['Lenovo', 'Lenovo', 'Lenovo', 'Lenovo', 'Lenovo'],
        'categories': [
            ['Notebooks', 'Ultrabooks'],
            ['Notebooks', 'Gamer'],
            ['Notebooks', '2 en 1'],
            ['PC de Escritorio', 'Mini PC'],
            ['Monitores', '4K']
        ],
        'list_price': [250000, 180000, 220000, 150000, 120000],
        'sale_price': [225000, 162000, 198000, 135000, 108000],
        'sku_id': ['20KH001UAR', '81Y4000QAR', '82BJ000BAR', '11T3000VAR', '61B8GAR1AR']
    }

    df = pd.DataFrame(sample_data)
    return df

# Cargar modelo spaCy
def load_spacy_model():
    if not SPACY_AVAILABLE:
        return None

    try:
        nlp = spacy.load("model-best")
        return nlp
    except Exception as e:
        print(f"Error cargando el modelo spaCy: {e}")
        return None

# Función para predecir etiquetas de una consulta
def predict_labels(query: str, nlp) -> Dict[str, float]:
    if not nlp:
        return {}

    doc = nlp(query)
    predictions = {}

    # Obtener las predicciones del textcat_multilabel
    if hasattr(doc.cats, 'items'):
        predictions = dict(doc.cats)
    else:
        # Fallback si la estructura es diferente
        predictions = doc.cats

    return predictions

# Función para calcular score de un producto basado en las predicciones
def calculate_product_score(product: pd.Series, predictions: Dict[str, float]) -> float:
    score = 0.0

    # Mapeo de categorías de productos a etiquetas del modelo
    category_mapping = {
        'Notebooks': ['CAT_NOTEBOOK'],
        'Ultrabooks': ['CAT_NOTEBOOK', 'ATTR_LIGERA'],
        'Gamer': ['CAT_NOTEBOOK', 'INT_GAMING', 'ATTR_GRAFICA_DEDICADA'],
        '2 en 1': ['CAT_NOTEBOOK', 'ATTR_2_EN_1'],
        'PC de Escritorio': ['CAT_PC_ESCRITORIO'],
        'Mini PC': ['CAT_PC_ESCRITORIO', 'ATTR_COMPACTO'],
        'Monitores': ['CAT_MONITOR'],
        '4K': ['CAT_MONITOR', 'ATTR_ALTA_RESOLUCION'],
        'Teclados': ['CAT_TECLADO'],
        'Mecánicos': ['CAT_TECLADO', 'ATTR_MECANICO'],
        'RGB': ['CAT_TECLADO', 'ATTR_RGB'],
        'Mouse': ['CAT_MOUSE'],
        'Gaming': ['CAT_MOUSE', 'INT_GAMING', 'ATTR_PRECISION_SENSOR'],
        'Inalámbricos': ['CAT_MOUSE', 'ATTR_INALAMBRICO']
    }

    # Mapeo de marcas
    brand_mapping = {
        'Lenovo': ['MARCA_LENOVO'],
        'Apple': ['MARCA_APPLE'],
        'Samsung': ['MARCA_SAMSUNG'],
        'Motorola': ['MARCA_MOTOROLA'],
        'Xiaomi': ['MARCA_XIAOMI'],
        'Google': ['MARCA_GOOGLE'],
        'OnePlus': ['MARCA_ONEPLUS'],
        'ASUS': ['MARCA_ASUS'],
        'Dell': ['MARCA_DELL'],
        'HP': ['MARCA_HP'],
        'Acer': ['MARCA_ACER'],
        'MSI': ['MARCA_MSI'],
        'LG': ['MARCA_LG']
    }

    # Verificar categorías del producto
    if isinstance(product.get('categories'), list):
        for category in product['categories']:
            if category in category_mapping:
                for label in category_mapping[category]:
                    if label in predictions:
                        score += predictions[label] * 2.0  # Peso mayor para categorías

    # Verificar marca del producto
    brand = product.get('brand_name', '')
    if brand in brand_mapping:
        for label in brand_mapping[brand]:
            if label in predictions:
                score += predictions[label] * 3.0  # Peso mayor para marcas

    # Verificar palabras clave en el título
    title_lower = product.get('title', '').lower()

    # Gaming keywords
    if any(word in title_lower for word in ['gaming', 'gamer', 'game', 'juego', 'juegos']):
        if 'INT_GAMING' in predictions:
            score += predictions['INT_GAMING'] * 2.0

    # Trabajo/oficina keywords
    if any(word in title_lower for word in ['trabajo', 'oficina', 'office', 'business']):
        if 'INT_OFICINA' in predictions:
            score += predictions['INT_OFICINA'] * 2.0
        if 'INT_TRABAJO' in predictions:
            score += predictions['INT_TRABAJO'] * 2.0

    # Programación keywords
    if any(word in title_lower for word in ['programacion', 'programación', 'desarrollo', 'developer', 'code']):
        if 'INT_PROGRAMACION' in predictions:
            score += predictions['INT_PROGRAMACION'] * 2.0

    return score

# Función de búsqueda inteligente
def intelligent_search(query: str, df: pd.DataFrame, nlp, top_k: int = 5) -> pd.DataFrame:
    if not query.strip() or not nlp:
        return df.head(top_k)

    # Obtener predicciones del modelo
    predictions = predict_labels(query, nlp)

    if not predictions:
        return df.head(top_k)

    # Calcular scores para todos los productos
    scores = []
    for idx, product in df.iterrows():
        score = calculate_product_score(product, predictions)
        scores.append((idx, score))

    # Ordenar por score descendente
    scores.sort(key=lambda x: x[1], reverse=True)

    # Tomar los top_k productos con mejor score
    top_indices = [idx for idx, score in scores[:top_k]]
    result_df = df.loc[top_indices].copy()

    # Agregar columna de score para mostrar
    result_df['relevance_score'] = [score for _, score in scores[:top_k]]

    return result_df

# Cargar datos y modelo
df = load_data()
nlp_model = load_spacy_model()

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index_moderno.html", {"request": request, "query": "", "filtered_df": None, "nlp_available": nlp_model is not None})

@app.post("/search", response_class=HTMLResponse)
async def search(request: Request, query: str = Form(...)):
    if query.strip() and nlp_model:
        filtered_df = intelligent_search(query, df, nlp_model, top_k=5)
    else:
        filtered_df = df.copy()
        if query.strip() and not nlp_model:
            # Mensaje de no disponible
            pass

    return templates.TemplateResponse("index_moderno.html", {"request": request, "query": query, "filtered_df": filtered_df.to_dict('records') if filtered_df is not None else None, "nlp_available": nlp_model is not None})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)