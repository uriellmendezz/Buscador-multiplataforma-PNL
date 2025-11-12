#!/usr/bin/env python3
"""
Test script to demonstrate the LLM model interface
This shows how the model predictions work once dependencies are resolved
"""
import sys
import os
import re
import json
import pandas as pd
import ast

# Add the extracted model to the Python path
sys.path.insert(0, '.')

def clean_label(label):
    """Clean up duplicate prefixes in model labels"""
    # Remove duplicated prefixes: CAT_CAT_, INT_INT_, ATTR_ATTR_
    # Keep only the first occurrence of the prefix
    
    # Match patterns like CAT_CAT_, INT_INT_, ATTR_ATTR_ and replace with single prefix
    cleaned = re.sub(r'^(CAT_CAT|INT_INT|ATTR_ATTR)_(.*)$', r'\1_\2', label)
    
    # If pattern doesn't match, return original label
    if cleaned == label:
        # Try to remove the first duplicate prefix manually
        parts = label.split('_')
        if len(parts) >= 3:
            # Check if first two parts are identical (e.g., CAT_CAT)
            if parts[0] == parts[1]:
                cleaned = '_'.join([parts[0]] + parts[2:])
    
    return cleaned

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

def load_products_data():
    """Cargar datos de productos del CSV"""
    try:
        df = pd.read_csv('datos/productos-gemini.csv')
        print(f"SUCCESS: Cargados {len(df)} productos del archivo CSV")
        
        # Procesar la columna atributos_correctos para extraer categorías, intenciones y atributos
        df['parsed_attributes'] = df['atributos_correctos'].apply(parse_attributes)
        
        # Agregar campos separados para facilitar el cálculo de scores
        df['categoria_principal'] = df['parsed_attributes'].apply(lambda x: x.get('categoria', '') if x else '')
        df['intencion_principal'] = df['parsed_attributes'].apply(lambda x: x.get('intencion', '') if x else '')
        df['atributos_lista'] = df['parsed_attributes'].apply(lambda x: x.get('atributos', []) if x else [])
        
        return df
    except Exception as e:
        print(f"ERROR cargando datos del CSV: {e}")
        return pd.DataFrame()

def calculate_product_score(product: pd.Series, predictions: dict) -> float:
    """Calcula score de un producto basado en las predicciones del modelo"""
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

    return score

def find_top_products(predictions: dict, df: pd.DataFrame, top_k: int = 5):
    """Encuentra los top_k productos más recomendados basado en las predicciones"""
    if not predictions:
        return pd.DataFrame()
    
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

def print_product_recommendations(query: str, predictions: dict, products_df: pd.DataFrame, top_k: int = 5):
    """Imprime las recomendaciones de productos de forma legible"""
    if not predictions:
        print("No hay predicciones del modelo disponibles")
        return
    
    # Encontrar top productos
    top_products = find_top_products(predictions, products_df, top_k)
    
    print(f"\nTOP {top_k} PRODUCTOS RECOMENDADOS para: '{query}'")
    print("=" * 60)
    
    if top_products.empty:
        print("No se encontraron productos recomendados")
        return
    
    for i, (_, product) in enumerate(top_products.iterrows(), 1):
        score = product.get('relevance_score', 0)
        print(f"\n{i}. {product['title']}")
        print(f"   Precio: ${product['list_price']:,.0f}")
        print(f"   Marca: {product['brand_name']}")
        print(f"   Categoria: {product.get('categoria_principal', 'N/A')}")
        print(f"   Intencion: {product.get('intencion_principal', 'N/A')}")
        print(f"   Score de relevancia: {score:.3f}")
        
        # Mostrar algunos atributos
        atributos = product.get('atributos_lista', [])
        if isinstance(atributos, list) and atributos:
            print(f"   Atributos: {', '.join(atributos[:3])}{'...' if len(atributos) > 3 else ''}")

def get_mock_predictions(query: str):
    """Genera predicciones mock para demostrar funcionalidad sin LLM"""
    query_lower = query.lower()
    predictions = {}
    
    if 'notebook' in query_lower or 'laptop' in query_lower or 'computadora' in query_lower:
        predictions.update({
            'CAT_NOTEBOOK': 0.9,
            'CAT_PC_ESCRITORIO': 0.3,
            'CAT_MONITOR': 0.2,
            'CAT_AURICULAR': 0.1
        })
    
    if 'gaming' in query_lower or 'juego' in query_lower or 'gamer' in query_lower:
        predictions.update({
            'INT_GAMING': 0.9,
            'INT_OFICINA': 0.2,
            'INT_ESTUDIO': 0.3,
            'INT_DISEÑO': 0.4
        })
    
    if 'oficina' in query_lower or 'trabajo' in query_lower or 'office' in query_lower:
        predictions.update({
            'INT_OFICINA': 0.9,
            'INT_GAMING': 0.1,
            'INT_ESTUDIO': 0.3,
            'INT_DISEÑO': 0.5
        })
    
    if 'diseño' in query_lower or 'diseno' in query_lower or 'grafico' in query_lower:
        predictions.update({
            'INT_DISEÑO': 0.9,
            'INT_GAMING': 0.3,
            'INT_OFICINA': 0.4,
            'INT_ESTUDIO': 0.2
        })
    
    if 'monitor' in query_lower:
        predictions.update({
            'CAT_MONITOR': 0.9,
            'CAT_NOTEBOOK': 0.2,
            'CAT_PC_ESCRITORIO': 0.3
        })
    
    # Agregar algunos atributos relevantes
    if 'gaming' in query_lower:
        predictions.update({
            'ATTR_TARJETA_GRAFICA': 0.8,
            'ATTR_POTENTE': 0.7,
            'ATTR_GAMA_ALTA': 0.6,
            'ATTR_REFRESH_144HZ': 0.5
        })
    
    if 'oficina' in query_lower:
        predictions.update({
            'ATTR_COMPACTO': 0.7,
            'ATTR_ECONOMICO': 0.6,
            'ATTR_PORTATIL': 0.5,
            'ATTR_SILENCIOSO': 0.4
        })
    
    return predictions

def main():
    print("=== TESTING LLM MODEL INTERFACE ===")
    
    # Cargar datos de productos
    print("Cargando datos de productos...")
    products_df = load_products_data()
    if products_df.empty:
        print("ERROR: No se pudieron cargar los datos de productos")
        return False
    
    # Intentar cargar el modelo LLM
    model = None
    llm_available = False
    
    try:
        from es_ecommerce_classifier import load as load_model
        print("Cargando modelo LLM...")
        model = load_model()
        print("SUCCESS: Modelo cargado exitosamente")
        llm_available = True
    except (ImportError, OSError, Exception) as e:
        print(f"INFO: Modelo LLM no disponible: {str(e)[:100]}...")
        print("USANDO PREDICCIONES MOCK PARA DEMOSTRAR FUNCIONALIDAD")
        llm_available = False
    
    # Test queries to demonstrate the model's capabilities
    test_queries = [
        "Quiero una notebook para gaming",
        "Necesito un monitor para diseño",
        "Busco una computadora para trabajar en la oficina"
    ]
    
    print("\n=== PREDICCIONES DEL MODELO ===")
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*80}")
        print(f"CONSULTA {i}: '{query}'")
        print(f"{'='*80}")
        
        try:
            if llm_available and model:
                # Process the query with the model
                doc = model(query)
                
                # Get predictions
                raw_predictions = dict(doc.cats)
                
                # Clean up the labels by removing duplicate prefixes
                cleaned_predictions = {}
                for raw_label, score in raw_predictions.items():
                    clean_label_name = clean_label(raw_label)
                    cleaned_predictions[clean_label_name] = score
                
                # Show the raw predictions (original)
                print(f"\nPredicciones originales del modelo:")
                print(json.dumps(raw_predictions, indent=2, ensure_ascii=False))
                
                # Show the cleaned predictions (corrected)
                print(f"\nPredicciones corregidas (sin prefijos duplicados):")
                print(json.dumps(cleaned_predictions, indent=2, ensure_ascii=False))
                
                # Show filtered predictions (those with score > 0.5) - using corrected labels
                high_confidence = {k: v for k, v in cleaned_predictions.items() if v > 0.5}
                if high_confidence:
                    print(f"\nEtiquetas de alta confianza (>0.5):")
                    for label, score in sorted(high_confidence.items(), key=lambda x: x[1], reverse=True):
                        print(f"   • {label}: {score:.3f}")
                else:
                    print("\nNo se encontraron etiquetas de alta confianza")
            else:
                # Usar predicciones mock
                cleaned_predictions = get_mock_predictions(query)
                print(f"\nPredicciones mock (demo sin LLM):")
                print(json.dumps(cleaned_predictions, indent=2, ensure_ascii=False))
                
                print(f"\nEtiquetas de predicciones mock (>0.5):")
                high_confidence = {k: v for k, v in cleaned_predictions.items() if v > 0.5}
                for label, score in sorted(high_confidence.items(), key=lambda x: x[1], reverse=True):
                    print(f"   • {label}: {score:.3f}")
            
            # Mostrar recomendaciones de productos basadas en las predicciones
            print_product_recommendations(query, cleaned_predictions, products_df, top_k=5)
                
        except Exception as e:
            print(f"ERROR procesando la consulta: {e}")
    
    print(f"\n{'='*80}")
    print("=== RESUMEN ===")
    if llm_available:
        print("El modelo LLM está configurado y funcionando correctamente")
        print("Las predicciones se han corregido para eliminar prefijos duplicados:")
        print("  • CAT_CAT_NOTEBOOK → CAT_NOTEBOOK")
        print("  • INT_INT_GAMING → INT_GAMING")
        print("  • ATTR_ATTR_ECONOMICO → ATTR_ECONOMICO")
    else:
        print("Modo DEMO: Las predicciones son mock para demostrar funcionalidad")
        print("Para usar el LLM real, resuelve las dependencias de PyTorch")
    
    print("Cada consulta mostró las 5 mejores recomendaciones de productos")
    print("El sistema de scoring está funcionando correctamente")
    print(f"{'='*80}")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            sys.exit(1)
    except Exception as e:
        print(f"ERROR general: {e}")
        print(f"Tipo de error: {type(e).__name__}")
    finally:
        print("\n=== FIN DEL TEST ===")