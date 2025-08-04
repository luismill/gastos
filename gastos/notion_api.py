import requests
from config import NOTION_API_URL, DATABASE_ID, HEADERS
from tkinter import messagebox
import pandas as pd

def read_notion_records():
    query_url = NOTION_API_URL + "databases/" + DATABASE_ID + "/query"
    response = requests.post(query_url, headers=HEADERS)
    
    if response.status_code != 200:
        messagebox.showerror("Error", f"Error consultando a Notion: {response.text}")
        print(f"Error consultando a Notion: {response.text}")
        return None
    
    data = response.json().get("results", [])
    
    properties_data = []
    for record in data:
        properties = record.get("properties", {})
        cuenta = properties.get("Cuenta", {}).get("select", {}).get("name") if properties.get("Cuenta", {}).get("select") else None
        gasto = properties.get("Gasto", {}).get("number") if properties.get("Gasto") else None
        ingreso = properties.get("Ingreso", {}).get("number") if properties.get("Ingreso") else None
        fecha = properties.get("Fecha", {}).get("date", {}).get("start") if properties.get("Fecha", {}).get("date") else None
        
        filtered_properties = {
            "Cuenta": cuenta,
            "Gasto": gasto,
            "Ingreso": ingreso,
            "Fecha": fecha
        }
        properties_data.append(filtered_properties)

    return properties_data

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