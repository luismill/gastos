import requests
from config import NOTION_API_URL, DATABASE_ID, HEADERS
from tkinter import messagebox
import pandas as pd


def _parse_property_value(prop: dict):
    """Convert a Notion property value into a basic Python datatype."""
    prop_type = prop.get("type")

    if prop_type == "title":
        return "".join(part.get("plain_text", "") for part in prop.get("title", []))
    if prop_type == "rich_text":
        return "".join(part.get("plain_text", "") for part in prop.get("rich_text", []))
    if prop_type == "number":
        return prop.get("number")
    if prop_type == "select":
        selected = prop.get("select")
        return selected.get("name") if selected else None
    if prop_type == "multi_select":
        return ", ".join(opt.get("name") for opt in prop.get("multi_select", []))
    if prop_type == "date":
        date = prop.get("date")
        return date.get("start") if date else None
    if prop_type == "checkbox":
        return prop.get("checkbox")
    if prop_type == "url":
        return prop.get("url")
    if prop_type == "email":
        return prop.get("email")
    if prop_type == "phone_number":
        return prop.get("phone_number")
    if prop_type == "relation":
        return ", ".join(rel.get("id") for rel in prop.get("relation", []))
    if prop_type == "people":
        return ", ".join(person.get("name") or person.get("id") for person in prop.get("people", []))
    if prop_type == "files":
        return ", ".join(f.get("name") for f in prop.get("files", []))

    # Fallback to raw string representation for unhandled types
    return str(prop.get(prop_type))


def read_notion_records():
    """Fetch all records from the Notion database, returning every column."""
    query_url = NOTION_API_URL + "databases/" + DATABASE_ID + "/query"
    response = requests.post(query_url, headers=HEADERS)

    if response.status_code != 200:
        messagebox.showerror("Error", f"Error consultando a Notion: {response.text}")
        print(f"Error consultando a Notion: {response.text}")
        return None

    data = response.json().get("results", [])

    records = []
    for record in data:
        properties = record.get("properties", {})
        parsed_properties = {}
        for name, prop in properties.items():
            parsed_properties[name] = _parse_property_value(prop)
        records.append(parsed_properties)

    return records


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

def insert_notion_record(nombre, fecha, cuenta, gasto=None, ingreso=None, subcategoria=None):
    url = NOTION_API_URL + "pages"
    properties = {
        "Nombre": {
            "title": [
                {
                    "text": {
                        "content": nombre
                    }
                }
            ]
        },
        "Fecha": {
            "date": {
                "start": fecha
            }
        },
        "Cuenta": {
            "select": {
                "name": cuenta
            }
        },
        "Script": {
            "checkbox": True
        }
    }
    
    if gasto is not None:
        properties["Gasto"] = {
            "number": gasto
        }
    
    if ingreso is not None:
        properties["Ingreso"] = {
            "number": ingreso
        }
    
    if subcategoria is not None:
        properties["Subcategoría"] = {
            "relation": [
                {
                    "id": subcategoria
                }
            ]
        }

    data = {
        "parent": {"database_id": DATABASE_ID},
        "properties": properties
    }

    url = "https://api.notion.com/v1/pages"
    response = requests.post(url, headers=HEADERS, json=data)
    
    if response.status_code != 200:
        messagebox.showerror("Error", f"Error insertando registro en Notion: {response.text}")
        return None
    
    return response.json()

def record_exists(records, fecha, cuenta, gasto=None, ingreso=None):
    """
    Check if a record with the same 'Fecha', 'Cuenta', 'Gasto', and 'Ingreso' already exists in the Notion database.
    """
    for record in records:
        if (
            record['Fecha'] == fecha and
            record['Cuenta'] == cuenta and
            ((gasto is not None and record['Gasto'] == gasto) or
             (ingreso is not None and record['Ingreso'] == ingreso))):
            return True
    return False

def get_category_ids(category_database_id):
    """
    Get the IDs of the categories from the related database and store them in a csv file.
    """
    url = NOTION_API_URL + "databases/" + category_database_id + "/query"
    response = requests.post(url, headers=HEADERS)
    
    if response.status_code != 200:
        print("Error consulting categories:", response.text)
        return None
    
    data = response.json().get("results", [])
    
    category_ids = {}
    for record in data:
        properties = record.get("properties", {})
        name = properties.get("Subcategoría", {}).get("title", [{}])[0].get("text", {}).get("content")
        category_id = record.get("id")
        if name and category_id:
            category_ids[name] = category_id
    df = pd.DataFrame(list(category_ids.items()), columns=['Categoria', 'ID'])
    df.to_csv('subcategorias.csv', index=False)
    
    return category_ids

if __name__ == "__main__":
    category_database_id = "abffbb24f06342558161af5162c82630"
    category_ids = get_category_ids(category_database_id)
    print("Category IDs:", category_ids)