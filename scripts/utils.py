import requests
import json
from env import HEADERS

def obtener_json(endpoint, params, timeout=20):
    r = requests.get(endpoint, params=params, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    return r.json()

def guardar_json(objeto, nombre_archivo: str):
    with open(nombre_archivo, "w", encoding="utf-8") as f:
        json.dump(objeto, f, ensure_ascii=False, indent=2)