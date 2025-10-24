import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from settings import NOTION_API_URL, DATABASE_ID, HEADERS
import pandas as pd
from typing import List, Dict, Optional


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


def read_notion_records(timeout: int = 15) -> Optional[List[Dict]]:
    query_url = NOTION_API_URL + "databases/" + DATABASE_ID + "/query"
    all_records: List[Dict] = []
    has_more = True
    next_cursor = None
    session = _session_with_retries()

    while has_more:
        payload = {}
        if next_cursor:
            payload["start_cursor"] = next_cursor
        response = session.post(query_url, headers=HEADERS, json=payload, timeout=timeout)
        if response.status_code != 200:
            return None
        data = response.json()
        all_records.extend(data.get("results", []))
        has_more = data.get("has_more", False)
        next_cursor = data.get("next_cursor", None)

    properties_data: List[Dict] = []
    for record in all_records:
        properties = record.get("properties", {})
        cuenta = properties.get("Cuenta", {}).get("select", {}).get("name") if properties.get("Cuenta", {}).get("select") else None
        gasto = properties.get("Gasto", {}).get("number") if properties.get("Gasto") else None
        ingreso = properties.get("Ingreso", {}).get("number") if properties.get("Ingreso") else None
        fecha = properties.get("Fecha", {}).get("date", {}).get("start") if properties.get("Fecha", {}).get("date") else None

        filtered_properties = {
            "Cuenta": cuenta,
            "Gasto": gasto,
            "Ingreso": ingreso,
            "Fecha": fecha,
        }
        properties_data.append(filtered_properties)

    return properties_data


def export_notion_to_csv(csv_path: str) -> bool:
    """Read records from Notion and export them to a CSV file.

    Parameters
    ----------
    csv_path:
        Destination path where the CSV will be saved.

    Returns
    -------
    bool
        ``True`` if the export was successful, ``False`` otherwise.
    """

    records = read_notion_records()
    if records is None:
        return False

    df = pd.DataFrame(records)
    try:
        df.to_csv(csv_path, index=False)
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo guardar el CSV: {e}")
        return False

    return True


def export_notion_to_csv(csv_path: str, timeout: int = 15) -> bool:
    """Exporta todos los registros de la base de datos Notion a un CSV con las columnas principales (paginación incluida)."""
    query_url = NOTION_API_URL + "databases/" + DATABASE_ID + "/query"
    all_records: List[Dict] = []
    has_more = True
    next_cursor = None
    session = _session_with_retries()

    while has_more:
        payload = {}
        if next_cursor:
            payload["start_cursor"] = next_cursor
        response = session.post(query_url, headers=HEADERS, json=payload, timeout=timeout)
        if response.status_code != 200:
            return False
        data = response.json()
        all_records.extend(data.get("results", []))
        has_more = data.get("has_more", False)
        next_cursor = data.get("next_cursor", None)

    rows = []

    def to_float(val):
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
                # ``plain_text`` is more broadly available than the deeply nested ``content``.
                return text.get("plain_text") or text.get("text", {}).get("content")

        if item_type == "rich_text":
            texts = first_item.get("rich_text", [])
            if texts:
                return texts[0].get("plain_text") or texts[0].get("text", {}).get("content")

        # Fallback to any stringified representation to avoid empty cells when data exists.
        return str(first_item) if first_item else None

    relation_title_cache: Dict[str, Optional[str]] = {}

    def fetch_relation_title(page_id: str) -> Optional[str]:
        if not page_id:
            return None

        if page_id in relation_title_cache:
            return relation_title_cache[page_id]

        page_url = NOTION_API_URL + "pages/" + page_id
        response = session.get(page_url, headers=HEADERS, timeout=timeout)

        title: Optional[str] = None
        if response.status_code == 200:
            properties = response.json().get("properties", {})
            for prop in properties.values():
                if prop.get("type") != "title":
                    continue

                titles = prop.get("title", [])
                if not titles:
                    continue

                text = titles[0]
                title = text.get("plain_text") or text.get("text", {}).get("content")
                if title:
                    break

        relation_title_cache[page_id] = title
        return title

    for record in all_records:
        props = record.get("properties", {})

        proyecto_viaje_relations = props.get("Proyecto / Viaje", {}).get("relation") or []
        proyecto_viaje_names = []
        for relation in proyecto_viaje_relations:
            related_page_id = relation.get("id")
            name = fetch_relation_title(related_page_id)
            if name:
                proyecto_viaje_names.append(name)

        row = {
            "Nombre": (
                props.get("Nombre", {}).get("title", [{}])[0].get("text", {}).get("content")
                if props.get("Nombre", {}).get("title")
                else None
            ),
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
            "Categoría": extract_rollup_value(
                props.get("Categoría", {}).get("rollup", {})
            ),
            "Proyecto / Viaje": ", ".join(proyecto_viaje_names) if proyecto_viaje_names else None,
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
    """Comprueba si existe un registro con misma fecha/cuenta e importe (gasto o ingreso) con tolerancia de floats."""
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
    """Obtiene ID y nombres de subcategorías y su categoría asociada."""
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
