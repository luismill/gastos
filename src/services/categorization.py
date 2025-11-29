import pandas as pd
import logging
from tkinter import messagebox
from pathlib import Path

# Adjust default path or pass it in
DEFAULT_RULES_PATH = Path("categorization_rules.xlsx")

def load_categorization_rules(file_path=None):
    if file_path is None:
        file_path = DEFAULT_RULES_PATH

    logging.info(f"Cargando reglas de categorización desde: {file_path}")
    try:
        if not Path(file_path).exists():
             # If not found in current dir, try one level up or specific location?
             # For now, just log warning.
             logging.warning(f"No se encontró el archivo de reglas: {file_path}")
             return pd.DataFrame()

        rules_df = pd.read_excel(file_path)
        if 'Prioridad' not in rules_df.columns:
            rules_df['Prioridad'] = 0
        rules_df = rules_df.sort_values(by='Prioridad', ascending=False).reset_index(drop=True)
        rules_df = rules_df.fillna('')
        logging.info(f"Reglas de categorización cargadas correctamente ({len(rules_df)} reglas).")
        return rules_df
    except Exception as e:
        logging.error(f"Error cargando reglas de categorización: {e}")
        # Remove GUI dependency (messagebox) from service layer if possible, or keep it if strictly needed.
        # But for 'clean architecture', services shouldn't pop up UI.
        # I'll remove messagebox and let the caller handle it or just log it.
        return pd.DataFrame()

def categorize_record(nombre, rules_df):
    if rules_df.empty:
        return None

    for _, rule in rules_df.iterrows():
        concept_contains = rule['Concepto_Contiene']
        concept_exact = rule['Concepto_Exacto']

        # Ensure we are comparing strings
        nombre_str = str(nombre) if nombre else ""

        if concept_exact and str(concept_exact) == nombre_str:
            return rule['Subcategoria_UUID'] if rule['Subcategoria_UUID'] else None
        elif concept_contains and str(concept_contains) in nombre_str:
            return rule['Subcategoria_UUID'] if rule['Subcategoria_UUID'] else None
    return None
