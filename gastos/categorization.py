import pandas as pd
import logging
from tkinter import messagebox

def load_categorization_rules(file_path="gastos/categorization_rules.xlsx"):
    logging.info(f"Cargando reglas de categorización desde: {file_path}")
    try:
        rules_df = pd.read_excel(file_path)
        if 'Prioridad' not in rules_df.columns:
            rules_df['Prioridad'] = 0
        rules_df = rules_df.sort_values(by='Prioridad', ascending=False).reset_index(drop=True)
        rules_df = rules_df.fillna('')
        logging.info(f"Reglas de categorización cargadas correctamente ({len(rules_df)} reglas).")
        return rules_df
    except FileNotFoundError:
        logging.error(f"No se encontró el archivo de reglas: {file_path}")
        messagebox.showerror("Error", f"No se encontró el archivo de reglas: {file_path}")
        return pd.DataFrame()
    except Exception as e:
        logging.error(f"Error cargando reglas de categorización: {e}")
        messagebox.showerror("Error", f"Error cargando reglas de categorización: {e}")
        return pd.DataFrame()

def categorize_record(nombre, rules_df):
    for _, rule in rules_df.iterrows():
        concept_contains = rule['Concepto_Contiene']
        concept_exact = rule['Concepto_Exacto']
        if concept_exact and nombre == concept_exact:
            return rule['Subcategoria_UUID'] if rule['Subcategoria_UUID'] else None
        elif concept_contains and concept_contains in nombre:
            return rule['Subcategoria_UUID'] if rule['Subcategoria_UUID'] else None
    return None