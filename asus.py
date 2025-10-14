import requests
import json
from pathlib import Path

HEADERS = {
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'es-419,es;q=0.5',
    'origin': 'https://www.asus.com',
    'priority': 'u=1, i',
    'referer': 'https://www.asus.com/',
    'sec-ch-ua': '"Brave";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-site',
    'sec-gpc': '1',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
}

# Configuro el maximo de resultos que quiero por petición
PAGE_SIZE = 300

def generar_datos(endpoint: str, nombre_archivo: str, params: dict | None = None,
                  page_size: int = PAGE_SIZE, timeout: int = 30) -> None:
    """Descarga productos paginando y guarda un JSON con la lista completa."""
    Path(nombre_archivo).parent.mkdir(parents=True, exist_ok=True)

    params = params.copy() if params else {}
    # si el endpoint ya trae querystring, requests respetará ambos. Preferimos params.
    params.setdefault("PageSize", str(page_size))

    page = 1
    all_products: list = []

    while True:
        params["PageIndex"] = str(page)
        resp = requests.get(endpoint, headers=HEADERS, params=params, timeout=timeout)
        try:
            resp.raise_for_status()
        except requests.HTTPError as e:
            raise RuntimeError(f"HTTP {resp.status_code} en {endpoint} (página {page}).") from e

        try:
            payload = resp.json()
        except ValueError as e:
            raise RuntimeError("La respuesta no es JSON válido.") from e

        # Estructuras tolerantes
        result = payload.get("Result", payload)
        product_list = result.get("ProductList") or result.get("productList") or []

        if not isinstance(product_list, list):
            raise RuntimeError("Formato inesperado: 'ProductList' no es una lista.")

        all_products.extend(product_list)

        # Cortamos si vino menos que el tamaño de página
        if len(product_list) < int(params["PageSize"]):
            break

        page += 1

    with open(nombre_archivo, "w", encoding="utf-8") as f:
        json.dump(all_products, f, ensure_ascii=False, indent=2)

## Notebooks

notebooks_params = {
    'SystemCode': 'asus',
    'WebsiteCode': 'ar',
    'ProductLevel1Code': 'laptops',
    'ProductLevel2Code': '',
    'PageSize': '200',
    'PageIndex': '1',
    'CategoryName': '',
    'SeriesName': '',
    'SubSeriesName': '',
    'Spec': '',
    'SubSpec': '',
    'PriceMin': '',
    'PriceMax': '',
    'Sort': 'Newsest',
    'siteID': 'www',
    'sitelang': '',
}

endpoints = [
    {
        'categoria': 'notebooks',
        'endpoint': 'https://odinapi.asus.com/recent-data/apiv2/SeriesFilterResult',
        'params': notebooks_params
    },

    {
        'categoria': 'monitores-pc-escritorio',
        'endpoint': 'https://odinapi.asus.com/recent-data/apiv2/SeriesFilterResult?SystemCode=asus&WebsiteCode=ar&ProductLevel1Code=displays-desktops&ProductLevel2Code=monitors&PageSize=300&PageIndex=1&CategoryName=&SeriesName=Gaming,ROG-Republic-of-Gamers,TUF-Gaming,ProArt,Eye-Care&SubSeriesName=&Spec=&SubSpec=&PriceMin=&PriceMax=&Sort=Recommend&siteID=www&sitelang='
    },

    {
        'categoria': 'tarjetas-madre',
        'endpoint': 'https://odinapi.asus.com/recent-data/apiv2/SeriesFilterResult?SystemCode=asus&WebsiteCode=ar&ProductLevel1Code=motherboards-components&ProductLevel2Code=motherboards&PageSize=300&PageIndex=1&CategoryName=Intel,AMD&SeriesName=&SubSeriesName=&Spec=&SubSpec=&PriceMin=&PriceMax=&Sort=&siteID=www&sitelang='
    },

    {
        'categoria': 'tarjetas-graficas',
        'endpoint': 'https://odinapi.asus.com/recent-data/apiv2/SeriesFilterResult?SystemCode=asus&WebsiteCode=ar&ProductLevel1Code=motherboards-components&ProductLevel2Code=graphics-cards&PageSize=300&PageIndex=1&CategoryName=AMD,NVIDIA&SeriesName=&SubSeriesName=&Spec=&SubSpec=&PriceMin=&PriceMax=&Sort=&siteID=www&sitelang='
    },

    {
        'categoria': 'enfriamiento',
        'endpoint': 'https://odinapi.asus.com/recent-data/apiv2/SeriesFilterResult?SystemCode=asus&WebsiteCode=ar&ProductLevel1Code=motherboards-components&ProductLevel2Code=cooling&PageSize=300&PageIndex=1&CategoryName=&SeriesName=ROG-Republic-of-Gamers,TUF-Gaming,ProArt,Prime&SubSeriesName=ROG-Ryujin,ROG-Ryuo,ROG-Strix-LC&Spec=&SubSpec=&PriceMin=&PriceMax=&Sort=Recommend&siteID=www&sitelang='
    },

    {
        'categoria': 'gabinetes',
        'endpoint': 'https://odinapi.asus.com/recent-data/apiv2/SeriesFilterResult?SystemCode=asus&WebsiteCode=ar&ProductLevel1Code=motherboards-components&ProductLevel2Code=cases&PageSize=300&PageIndex=1&CategoryName=&SeriesName=ROG-Republic-of-Gamers,TUF-Gaming,PRIME,ProArt&SubSeriesName=&Spec=&SubSpec=&PriceMin=&PriceMax=&Sort=&siteID=www&sitelang='
    },

    {
        'categoria': 'fuentes-poder',
        'endpoint': 'https://odinapi.asus.com/recent-data/apiv2/SeriesFilterResult?SystemCode=asus&WebsiteCode=ar&ProductLevel1Code=motherboards-components&ProductLevel2Code=power-supply-units&PageSize=300&PageIndex=1&CategoryName=&SeriesName=ROG-Republic-of-Gamers,TUF-Gaming,PRIME&SubSeriesName=ROG-Thor,ROG-Strix&Spec=&SubSpec=&PriceMin=&PriceMax=&Sort=Recommend&siteID=www&sitelang='
    },

    {
        'categoria': 'teclados',
        'endpoint': 'https://odinapi.asus.com/recent-data/apiv2/SeriesFilterResult?SystemCode=asus&WebsiteCode=ar&ProductLevel1Code=accessories&ProductLevel2Code=keyboards&PageSize=300&PageIndex=1&CategoryName=&SeriesName=ROG-Republic-of-Gamers,TUF-Gaming&SubSeriesName=&Spec=&SubSpec=&PriceMin=&PriceMax=&Sort=&siteID=www&sitelang='
    },

    {
        'categoria': 'mouse',
        'endpoint': 'https://odinapi.asus.com/recent-data/apiv2/SeriesFilterResult?SystemCode=asus&WebsiteCode=ar&ProductLevel1Code=accessories&ProductLevel2Code=mice-and-mouse-pads&PageSize=300&PageIndex=1&CategoryName=&SeriesName=ROG-Republic-of-Gamers,TUF-Gaming,ASUS-Mouse-and-Mouse-Pad&SubSeriesName=&Spec=&SubSpec=&PriceMin=&PriceMax=&Sort=&siteID=www&sitelang='
    },

    {
        'categoria': 'auriculares-audio',
        'endpoint': 'https://odinapi.asus.com/recent-data/apiv2/SeriesFilterResult?SystemCode=asus&WebsiteCode=ar&ProductLevel1Code=accessories&ProductLevel2Code=headsets-and-audio&PageSize=300&PageIndex=1&CategoryName=&SeriesName=ROG--Republic-of-Gamers,TUF-Gaming,Headsets-Accessories&SubSeriesName=&Spec=&SubSpec=&PriceMin=&PriceMax=&Sort=&siteID=www&sitelang='
    }
    
]

for dic in endpoints:
    outfile = f"datos/ASUS-{dic['categoria']}.json"
    generar_datos(dic["endpoint"], nombre_archivo=outfile, params=dic.get("params"))