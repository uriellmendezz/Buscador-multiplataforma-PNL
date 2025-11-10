import requests
from env import HEADERS, FRAVEGA_COOKIES
import time
import random
from utils import obtener_json, guardar_json
import pandas as pd
import json

page_size = 50


def obtener_productos(offset=0, page_size=50):
    json_data = {
        'operationName': 'listProducts_Shopping',
        'variables': {
            'customSorted': False,
            'isGeoLocated': True,
            'isSingleCategory': True,
            'filtering': {
                'keywords': {
                    'query': 'asus',
                },
                'availableStock': {
                    'postalCodes': 'X5000',
                    'includeThoseWithNoAvailableStockButListable': True,
                },
                'salesChannels': [
                    'fravega-ecommerce',
                ],
                'active': True,
            },
            'size': page_size,
            'offset': offset,
            'sorting': 'TOTAL_SALES_IN_LAST_30_DAYS',
        },
        'query': 'query listProducts_Shopping($size: PositiveInt!, $isSingleCategory: Boolean!, $offset: Int, $sorting: [SortOption!], $customSorted: Boolean = false, $filtering: ItemFilteringInputType, $isGeoLocated: Boolean = false) {\n  items(filtering: $filtering) {\n    total\n    recommendations {\n      keywords: products\n      __typename\n    }\n    results(\n      size: $size\n      buckets: [{sorting: $sorting, customSorted: $customSorted, offset: $offset}]\n    ) {\n      ...extendedItemFragment\n      __typename\n    }\n    aggregations {\n      availableStock @include(if: $isGeoLocated) {\n        ...availabilityStockAggregation\n        __typename\n      }\n      sellerCondition(size: $size) {\n        cardinality\n        values {\n          count\n          filtered\n          condition\n          __typename\n        }\n        __typename\n      }\n      collections(aggregable: true) {\n        values {\n          ...collectionAggregationFragment\n          __typename\n        }\n        __typename\n      }\n      installments {\n        values {\n          ...collectionAggregationFragment\n          __typename\n        }\n        __typename\n      }\n      categories(market: "fravega", flattened: $isSingleCategory) {\n        ...categoryAggregationFragment\n        children {\n          ...categoryAggregationFragment\n          __typename\n        }\n        __typename\n      }\n      attributes {\n        ...attributeAggregationFragment\n        __typename\n      }\n      salePrice {\n        ...rangedSalePriceAggregationFragment\n        __typename\n      }\n      brands {\n        cardinality\n        values(size: 6, sorting: FREQUENCY) {\n          ...brandAggregationFragment\n          __typename\n        }\n        __typename\n      }\n      __typename\n    }\n    listUniqueId\n    __typename\n  }\n}\n\nfragment extendedItemFragment on ExtendedItem {\n  sellers {\n    commercialName\n    __typename\n  }\n  stockLabels\n  id\n  title\n  katalogCategoryId\n  brand {\n    id\n    name\n    __typename\n  }\n  skus {\n    results {\n      code\n      categorization(market: "fravega") {\n        name\n        slug\n        __typename\n      }\n      resolvedBidId\n      sponsored\n      campaignId\n      pricing(channel: "fravega-ecommerce") {\n        channel\n        listPrice\n        salePrice\n        discount\n        __typename\n      }\n      netPricing: pricing(channel: "net-price") {\n        channel\n        listPrice\n        salePrice\n        discount\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n  gtin {\n    __typename\n    ... on EAN {\n      number\n      __typename\n    }\n  }\n  id\n  images\n  collections(onlyThoseWithCockade: true) {\n    cardinality\n    values {\n      id\n      name\n      slug\n      count\n      cockade(tag: "listing") {\n        position\n        image\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n  installments {\n    cardinality\n    values {\n      id\n      name\n      slug\n      count\n      cockade(tag: "listing") {\n        position\n        image\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n  listPrice {\n    amounts {\n      min\n      max\n      __typename\n    }\n    __typename\n  }\n  salePrice {\n    amounts {\n      min\n      max\n      __typename\n    }\n    discounts {\n      min\n      max\n      __typename\n    }\n    __typename\n  }\n  slug\n  __typename\n}\n\nfragment availabilityStockAggregation on AvailabilityStockAggregation {\n  deliveryTerms {\n    value\n    count\n    __typename\n  }\n  types {\n    value\n    count\n    __typename\n  }\n  costs {\n    value\n    count\n    __typename\n  }\n  __typename\n}\n\nfragment collectionAggregationFragment on CollectionAggregation {\n  id\n  name\n  count\n  slug\n  filtered\n  __typename\n}\n\nfragment categoryAggregationFragment on CategoryAggregation {\n  name\n  slug\n  count\n  path {\n    id\n    name\n    slug\n    __typename\n  }\n  children {\n    name\n    slug\n    count\n    path {\n      id\n      name\n      slug\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n\nfragment attributeAggregationFragment on AttributeAggregation {\n  name\n  slug\n  tags\n  measureUnit {\n    name\n    symbol\n    __typename\n  }\n  values(size: 20) {\n    type\n    value\n    slug\n    count\n    seo\n    filtered\n    __typename\n  }\n  ranges {\n    from\n    to\n    count\n    value\n    slug\n    seo\n    filtered {\n      from\n      to\n      value\n      slug\n      seo\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n\nfragment rangedSalePriceAggregationFragment on RangedSalePriceAggregation {\n  amounts {\n    ranges(size: 3) {\n      from\n      to\n      count\n      value\n      slug\n      __typename\n    }\n    min\n    max\n    __typename\n  }\n  discounts {\n    ranges(interval: 10) {\n      from\n      count\n      value\n      slug\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n\nfragment brandAggregationFragment on BrandAggregation {\n  name\n  count\n  slug\n  image\n  filtered\n  __typename\n}\n',
    }

    response = requests.post('https://www.fravega.com/api/v1', cookies=FRAVEGA_COOKIES, headers=HEADERS, json=json_data)
    return response

def generar_json(response: requests.Response):
    try:
        return response.json()
    except:
        raise Exception('No se pudo convertir a JSON la respuesta.')
    
def transformaciones(data_json: dict):
    productos = data_json["data"]["items"]["results"]

    df = pd.DataFrame(productos)
    df = df[['id', 'title', 'katalogCategoryId', 'brand', 'skus','slug']]
    df = pd.json_normalize(df.to_dict('records'), sep='_')
    df = df.drop(columns=['brand___typename','skus___typename'], axis=1)


    def ensure_list(v):
        return v if isinstance(v, list) else []

    def first_list(v):
        return v[0] if isinstance(v, list) and v else None

    def get_category_names(categ):
        """
        'categ' suele ser una lista de rutas (cada ruta es una lista de dicts con name/slug).
        Retorna una lista con todos los nombres de categorías.
        """
        if not isinstance(categ, list) or not categ:
            return []
        ruta = categ[0]
        if not isinstance(ruta, list):
            return []
        return [x.get("name") for x in ruta if isinstance(x, dict)]

    # ---------- 1) Exploto SKUs: una fila por SKU ----------
    tmp = df.copy()
    tmp["skus_results"] = tmp["skus_results"].apply(ensure_list)
    tmp = tmp.explode("skus_results", ignore_index=True)

    # Normalizo el dict del SKU en columnas
    sku_cols = pd.json_normalize(tmp["skus_results"]).add_prefix("sku_")
    tmp = tmp.drop(columns=["skus_results"]).join(sku_cols)

    # ---------- 2) Exploto pricing ----------
    tmp["sku_pricing"] = tmp["sku_pricing"].apply(ensure_list)
    tmp = tmp.explode("sku_pricing", ignore_index=True)
    pricing_cols = pd.json_normalize(tmp["sku_pricing"]).add_prefix("pricing_")
    tmp = tmp.drop(columns=["sku_pricing"]).join(pricing_cols)

    # ---------- 3) Priorizar canal 'fravega-ecommerce' ----------
    tmp["_pref_order"] = (tmp["pricing_channel"] != "fravega-ecommerce").astype(int)
    tmp = tmp.sort_values(["sku_code", "_pref_order"]).drop_duplicates(subset=["sku_code"], keep="first").drop(columns=["_pref_order"])

    # ---------- 4) Obtener categorías como lista ----------
    tmp["categories"] = tmp["sku_categorization"].apply(get_category_names)

    # ---------- 5) Selección final ----------
    df_skus = tmp[[
        "id",                 # ID del producto
        "sku_code",           # Código del SKU
        "categories",         # Lista de categorías
        "pricing_listPrice",  # Precio de lista
        "pricing_salePrice"   # Precio de oferta
    ]].rename(columns={
        "sku_code": "sku_id",
        "pricing_listPrice": "list_price",
        "pricing_salePrice": "sale_price"
    })

    return df.merge(df_skus, on='id').drop('skus_results', axis=1)



if __name__ == '__main__':
    
