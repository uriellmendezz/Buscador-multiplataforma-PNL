import requests
import json

HEADERS = {
    'accept': '*/*',
    'accept-language': 'es-419,es;q=0.6',
    'origin': 'https://www.lenovo.com',
    'priority': 'u=1, i',
    'referer': 'https://www.lenovo.com/',
    'sec-ch-ua': '"Brave";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-site',
    'sec-gpc': '1',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
}

def obtener_json(endpoint, params, timeout=20):
    r = requests.get(endpoint, params=params, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    return r.json()

def guardar_json(objeto, nombre_archivo: str):
    with open(nombre_archivo, "w", encoding="utf-8") as f:
        json.dump(objeto, f, ensure_ascii=False, indent=2)