import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from typing import Dict, Iterable, List, Optional, Set, Tuple

import pandas as pd

from settings import (
    DATABASE_ID,
    HEADERS,
    NOTION_API_URL,
    PROJECT_DATABASE_ID,
)


def _session_with_retries() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["POST", "GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def _normalize_property_name(name: str) -> str:
    return name.lower().replace(" ", "")


def _get_property(properties: Dict, target: str) -> Optional[Dict]:
    normalized_target = _normalize_property_name(target)
    for key, value in properties.items():
        if _normalize_property_name(key) == normalized_target:
            return value
    return None


def _extract_title_from_properties(properties: Dict) -> Optional[str]:
    for prop in properties.values():
        if prop.get("type") != "title":
            continue

        titles = prop.get("title", [])
        for text in titles:
            plain = text.get("plain_text")
            if plain:
                return plain
            rich_text = text.get("text", {}).get("content")
            if rich_text:
                return rich_text
    return None


def _query_database(
    database_id: str, session: requests.Session, timeout: int
) -> Tuple[List[Dict], bool]:
    query_url = f"{NOTION_API_URL}databases/{database_id}/query"
    has_more = True
    next_cursor: Optional[str] = None
    results: List[Dict] = []
    success = True

    while has_more:
        payload: Dict = {}
        if next_cursor:
            payload["start_cursor"] = next_cursor
        response = session.post(query_url, headers=HEADERS, json=payload, timeout=timeout)
        if response.status_code != 200:
            success = False
            break
        data = response.json()
        results.extend(data.get("results", []))
        has_more = data.get("has_more", False)
        next_cursor = data.get("next_cursor")

    return results, success


def read_notion_records(timeout: int = 15) -> Optional[List[Dict]]:
    session = _session_with_retries()
    raw_records, success = _query_database(DATABASE_ID, session, timeout)
    if not success:
        return None

    records: List[Dict] = []

    for record in raw_records:
        properties = record.get("properties", {})
        cuenta_select = properties.get("Cuenta", {}).get("select") if properties.get("Cuenta") else None
        fecha_data = properties.get("Fecha", {}).get("date") if properties.get("Fecha") else None

        records.append(
            {
                "Cuenta": cuenta_select.get("name") if cuenta_select else None,
                "Gasto": properties.get("Gasto", {}).get("number"),
                "Ingreso": properties.get("Ingreso", {}).get("number"),
                "Fecha": fecha_data.get("start") if fecha_data else None,
            }
        )

    return records


def _collect_relation_ids(records: Iterable[Dict]) -> Set[str]:
    relation_ids: Set[str] = set()
    for record in records:
        properties = record.get("properties", {})
        relation_prop = _get_property(properties, "Proyecto/Viaje")
        if not relation_prop:
            continue
        for relation in relation_prop.get("relation", []):
            page_id = relation.get("id")
            if page_id:
                relation_ids.add(page_id)
    return relation_ids


def _fetch_project_titles_from_database(
    session: requests.Session, target_ids: Set[str], timeout: int
) -> Dict[str, Optional[str]]:
    if not PROJECT_DATABASE_ID or not target_ids:
        return {}

    titles: Dict[str, Optional[str]] = {}
    pages, success = _query_database(PROJECT_DATABASE_ID, session, timeout)
    if not success:
        return titles

    for page in pages:
        page_id = page.get("id")
        if page_id not in target_ids:
            continue
        title = _extract_title_from_properties(page.get("properties", {}))
        titles[page_id] = title
        if len(titles) == len(target_ids):
            break
    return titles


def _fetch_page_title(
    session: requests.Session, page_id: str, timeout: int
) -> Optional[str]:
    if not page_id:
        return None

    page_url = f"{NOTION_API_URL}pages/{page_id}"
    response = session.get(page_url, headers=HEADERS, timeout=timeout)
    if response.status_code != 200:
        return None

    return _extract_title_from_properties(response.json().get("properties", {}))


def export_notion_to_csv(csv_path: str, timeout: int = 15) -> bool:
    session = _session_with_retries()
    all_records, success = _query_database(DATABASE_ID, session, timeout)
    if not success:
        return False

    relation_ids = _collect_relation_ids(all_records)
    relation_title_cache = _fetch_project_titles_from_database(
        session, relation_ids, timeout
    )

    rows: List[Dict[str, Optional[str]]] = []

    def to_float(val: Optional[float]) -> Optional[float]:
        return float(val) if val is not None else None

    def extract_rollup_value(rollup: Dict) -> Optional[str]:
        if not rollup:
            return None

        array = rollup.get("array", [])
        if not array:
            return None

        first_item = array[0]
        item_type = first_item.get("type")

        if item_type == "select":
            return first_item.get("select", {}).get("name")

        if item_type == "title":
            titles = first_item.get("title", [])
            if titles:
                text = titles[0]
                return text.get("plain_text") or text.get("text", {}).get("content")

        if item_type == "rich_text":
            texts = first_item.get("rich_text", [])
            if texts:
                return texts[0].get("plain_text") or texts[0].get("text", {}).get("content")

        return str(first_item) if first_item else None

    for record in all_records:
        props = record.get("properties", {})

        proyecto_prop = _get_property(props, "Proyecto/Viaje")
        proyecto_relations = proyecto_prop.get("relation") if proyecto_prop else []
        proyecto_names: List[str] = []
        for relation in proyecto_relations or []:
            related_page_id = relation.get("id")
            if not related_page_id:
                continue
            if related_page_id not in relation_title_cache:
                relation_title_cache[related_page_id] = _fetch_page_title(session, related_page_id, timeout)
            name = relation_title_cache.get(related_page_id)
            if name:
                proyecto_names.append(name)

        row = {
            "Nombre": _extract_title_from_properties(props) or None,
            "Fecha": (
                props.get("Fecha", {}).get("date", {}).get("start")
                if props.get("Fecha", {}).get("date")
                else None
            ),
            "Cuenta": (
                props.get("Cuenta", {}).get("select", {}).get("name")
                if props.get("Cuenta", {}).get("select")
                else None
            ),
            "Gasto": to_float(props.get("Gasto", {}).get("number")),
            "Ingreso": to_float(props.get("Ingreso", {}).get("number")),
            "Transferencias": to_float(props.get("Transferencias", {}).get("number")),
            "Subcategoría": (
                props.get("Subcategoría", {}).get("relation", [{}])[0].get("id")
                if props.get("Subcategoría", {}).get("relation")
                else None
            ),
            "Categoría": extract_rollup_value(props.get("Categoría", {}).get("rollup", {})),
            "Proyecto/Viaje": ", ".join(proyecto_names) if proyecto_names else None,
            "Script": props.get("Script", {}).get("checkbox"),
            "Mes": (
                props.get("Mes", {}).get("formula", {}).get("string")
                if props.get("Mes", {}).get("formula")
                else None
            ),
            "url": record.get("url"),
        }
        rows.append(row)

    try:
        df = pd.DataFrame(rows)
        df.to_csv(csv_path, index=False, decimal=",", sep=";")
    except Exception:
        return False

    return True


def insert_notion_record(
    nombre,
    fecha,
    cuenta,
    gasto=None,
    ingreso=None,
    subcategoria=None,
    timeout: int = 15,
):
    url = NOTION_API_URL + "pages"
    properties = {
        "Nombre": {"title": [{"text": {"content": nombre}}]},
        "Fecha": {"date": {"start": fecha}},
        "Cuenta": {"select": {"name": cuenta}},
        "Script": {"checkbox": True},
    }

    if gasto is not None:
        properties["Gasto"] = {"number": gasto}

    if ingreso is not None:
        properties["Ingreso"] = {"number": ingreso}

    if subcategoria is not None:
        properties["Subcategoría"] = {"relation": [{"id": subcategoria}]}

    data = {"parent": {"database_id": DATABASE_ID}, "properties": properties}

    session = _session_with_retries()
    response = session.post(url, headers=HEADERS, json=data, timeout=timeout)
    if response.status_code != 200:
        return None

    return response.json()


def record_exists(
    records: List[Dict],
    fecha: str,
    cuenta: str,
    gasto: Optional[float] = None,
    ingreso: Optional[float] = None,
) -> bool:
    from math import isclose

    for record in records:
        if record.get("Fecha") != fecha or record.get("Cuenta") != cuenta:
            continue

        if gasto is not None and record.get("Gasto") is not None:
            if isclose(float(record["Gasto"]), float(gasto), rel_tol=1e-09, abs_tol=0.001):
                return True
        if ingreso is not None and record.get("Ingreso") is not None:
            if isclose(float(record["Ingreso"]), float(ingreso), rel_tol=1e-09, abs_tol=0.001):
                return True
    return False


def fetch_category_rows(category_database_id: str, timeout: int = 15):
    url = NOTION_API_URL + "databases/" + category_database_id + "/query"
    session = _session_with_retries()
    response = session.post(url, headers=HEADERS, timeout=timeout)
    if response.status_code != 200:
        return None

    data = response.json().get("results", [])
    rows = []
    for record in data:
        properties = record.get("properties", {})
        subcategoria = (
            properties.get("Subcategoría", {}).get("title", [{}])[0].get("text", {}).get("content")
        )
        select_obj = properties.get("Categoria", {}).get("select")
        categoria = select_obj.get("name") if select_obj else None
        subcategoria_id = record.get("id")
        rows.append(
            {
                "subcategoria_id": subcategoria_id,
                "subcategoria": subcategoria,
                "categoria": categoria,
            }
        )

    return rows


if __name__ == "__main__":
    pass
