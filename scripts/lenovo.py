import time, os, json
import requests
from utils import obtener_json, guardar_json, HEADERS
from urllib.parse import quote, unquote


def crear_carpeta_categoria(categoria: str):
    full_path = 'datos/lenovo/{}'.format(categoria)
    if not os.path.exists(full_path):
        os.makedirs(full_path)

    return full_path

def encoding(url_encoded, page):
    url_params = unquote(url_encoded)
    return quote(url_params.replace('"page":"1"', f'"page":"{page}"'), safe='')

def make_params(pageId, params):
    return {
        'pageFilterId': pageId,
        'subSeriesCode': '',
        'loyalty': 'false',
        'params': quote(str(params), safe=''),
    }

def obtener_datos(categoria, page_id, decoded_params, max_page=20, time_sleep=2):
    path_categoria = crear_carpeta_categoria(categoria)
    url = "https://openapi.lenovo.com/ar/es/ofp/search/dlp/product/query/get/_tsc"

    for page in range(0, MAX_PAGES):

        params = make_params(page_id, decoded_params)
        response = requests.get(url=url, headers=HEADERS, params=params)
        if response.status_code == 200:
            json_data = response.json()
            if json_data.get('status') == 200:
                with open(f'{path_categoria}/{categoria}-{page}.json', 'w', encoding="utf-8") as f:
                    json.dump(json_data, fp=f, ensure_ascii=False, indent=2)
                time.sleep(time_sleep)
        else:
            break

dict_categorias = [
    {
        'categoria': 'notebooks',
        'page_id': '0a64ace1-c4e1-4520-9197-5eecc03402cc',
        'decoded_params': '%7B%22classificationGroupIds%22%3A%22400001%22%2C%22pageFilterId%22%3A%2285803b1e-5106-4453-9710-26ed58925af3%22%2C%22facets%22%3A%5B%5D%2C%22page%22%3A%221%22%2C%22pageSize%22%3A20%2C%22groupCode%22%3A%22%22%2C%22init%22%3Atrue%2C%22sorts%22%3A%5B%22priceUp%22%5D%2C%22version%22%3A%22v2%22%2C%22enablePreselect%22%3Atrue%2C%22subseriesCode%22%3A%22%22%7D'
    }
]

### Notebooks
URL = ""
MAX_PAGES = 50
TIME_SLEEP = 2

# Computadoras escritorio
crear_carpeta_categoria('pc-escritorio')
escritorio_page_id = "85803b1e-5106-4453-9710-26ed58925af3"
