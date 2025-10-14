import requests
import json
from pathlib import Path

cookies = {
    'anonymous-consents': '%5B%5D',
    'cookie-notification': 'NOT_ACCEPTED',
    'JSESSIONID': '02453CB6A9D98722251F9BE1E10BA52B.accstorefront-76c55bc89d-2sskt',
    'HSESSION': '1',
    'ROUTE': '.accstorefront-76c55bc89d-2sskt',
}

headers = {
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'es-419,es;q=0.7',
    'priority': 'u=1, i',
    'referer': 'https://www.musimundo.com/informatica/notebook/c/98',
    'sec-ch-ua': '"Brave";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'sec-gpc': '1',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
    'x-requested-with': 'XMLHttpRequest',
    # 'cookie': 'anonymous-consents=%5B%5D; cookie-notification=NOT_ACCEPTED; JSESSIONID=02453CB6A9D98722251F9BE1E10BA52B.accstorefront-76c55bc89d-2sskt; HSESSION=1; ROUTE=.accstorefront-76c55bc89d-2sskt',
}

OUT = Path("data/notebooks-musimundo.jsonl")
OUT.parent.mkdir(parents=True, exist_ok=True)

with requests.Session() as s, OUT.open("a", encoding="utf-8") as f:
    for i in range(0, 10):
        try:
            params = {"q": ":relevance", "page": i}
            r = s.get("https://www.musimundo.com/informatica/notebook/c/c/98/results",
                      params=params, cookies=cookies, headers=headers, timeout=30)
            r.raise_for_status()
            data = r.json()
            productos = data.get("results", [])

            if not productos:  # sin resultados → corto paginación
                print('Sin más productos.')
                break

            print('Total de productos en la pagina:', len(productos))
            for p in productos:
                f.write(json.dumps(p, ensure_ascii=False) + "\n")

        except Exception as e:
            print(f"Página {i}: {e}")
