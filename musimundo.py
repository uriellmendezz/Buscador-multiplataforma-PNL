import requests
from pathlib import Path
import json

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

OUT = Path("datos/musimundo_notebooks.jsonl")
OUT.parent.mkdir(parents=True, exist_ok=True)

# (Opcional) Evitar duplicados por id/code/sku
ids_vistos = set()
if OUT.exists():
    with OUT.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                obj = json.loads(line)
                pid = str(obj.get("id") or obj.get("code") or obj.get("sku") or "")
                if pid:
                    ids_vistos.add(pid)
            except json.JSONDecodeError:
                pass

with requests.Session() as s, OUT.open("a", encoding="utf-8") as f_out:
    for i in range(1, 10):
        try:
            params = {"q": ":relevance", "page": i}
            r = s.get(
                "https://www.musimundo.com/informatica/notebook/c/c/98/results",
                params=params, cookies=COOKIES, headers=HEADERS, timeout=30
            )
            r.raise_for_status()
            data = r.json()
            productos = data.get("results", [])

            for p in productos:
                pid = str(p.get("id") or p.get("code") or p.get("sku") or "")
                if pid and pid in ids_vistos:
                    continue
                # apendá cada objeto en su propia línea
                f_out.write(json.dumps(p, ensure_ascii=False) + "\n")
                if pid:
                    ids_vistos.add(pid)

        except Exception as e:
            print(f"Página {i}: error -> {e}")



