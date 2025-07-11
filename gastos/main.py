import os
import logging
import pandas as pd
from bank_config import BankConfig
from notion_api import insert_notion_record, read_notion_records, record_exists
from file_processing import read_bank_records
from categorization import load_categorization_rules, categorize_record
from gui import create_main_window

# Crear carpeta logs si no existe
os.makedirs("logs", exist_ok=True)

# Configuración del logging
logging.basicConfig(
    filename='logs/gastos_app.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def clean_amount(value):
    return None if value is not None and pd.isna(value) else value

def process_record(
    record,
    existing_records,
    categorization_rules,
    successful_inserts,
    repeated_records
):
    nombre = record['Nombre']
    fecha = record['Fecha']
    cuenta = record['Cuenta']
    gasto = clean_amount(record['Gasto'])
    ingreso = clean_amount(record['Ingreso'])
    month = fecha.strftime('%Y-%m') if fecha is not None else None
    subcategoria = categorize_record(nombre, categorization_rules)

    if month and not record_exists(existing_records, fecha.strftime('%Y-%m-%d'), cuenta, gasto, ingreso):
        response = insert_notion_record(
            nombre,
            fecha.strftime('%Y-%m-%d'),
            cuenta,
            gasto=gasto,
            ingreso=ingreso,
            subcategoria=subcategoria
        )
        if response:
            successful_inserts[month] = successful_inserts.get(month, 0) + 1
            logging.info(f"Registro insertado: {nombre}, {fecha}, {cuenta}, gasto={gasto}, ingreso={ingreso}, subcategoria={subcategoria}")
        else:
            logging.warning(f"No se pudo insertar el registro: {nombre}, {fecha}, {cuenta}, gasto={gasto}, ingreso={ingreso}, subcategoria={subcategoria}")
    else:
        if month:
            repeated_records[month] = repeated_records.get(month, 0) + 1
            logging.info(f"Registro repetido (no insertado): {nombre}, {fecha}, {cuenta}, gasto={gasto}, ingreso={ingreso}")

def process_file(bank_name: str, file_path: str, status_label=None) -> None:
    try:
        logging.info(f"Inicio de procesamiento para banco: {bank_name}, archivo: {file_path}")
        if status_label:
            status_label.config(text="Procesando...", fg="blue")
            status_label.update_idletasks()

        bank = BankConfig(bank_name)
        data = read_bank_records(bank, file_path)

        categorization_rules = load_categorization_rules()
        if categorization_rules.empty:
            logging.warning("No se pudieron cargar las reglas de categorización.")
            if status_label:
                status_label.config(text="Error cargando reglas.", fg="red")
            return

        successful_inserts = {}
        repeated_records = {}

        existing_records = read_notion_records()
        logging.info("Registros existentes en Notion leídos.")

        if not data.empty:
            for _, record in data.iterrows():
                process_record(
                    record,
                    existing_records,
                    categorization_rules,
                    successful_inserts,
                    repeated_records
                )

            logging.info(f"Insertados exitosos por mes: {successful_inserts}")
            logging.info(f"Registros repetidos por mes: {repeated_records}")
            if status_label:
                status_label.config(
                    text=f"¡Proceso terminado!\nInsertados: {successful_inserts}\nRepetidos: {repeated_records}",
                    fg="green"
                )
        else:
            logging.warning("No se encontraron registros en el archivo.")
            if status_label:
                status_label.config(text="No se encontraron registros.", fg="orange")
    except Exception as e:
        logging.error(f"Error inesperado en el procesamiento: {e}", exc_info=True)
        if status_label:
            status_label.config(text=f"Error inesperado: {e}", fg="red")

if __name__ == "__main__":
    root = create_main_window(process_file)
    logging.info("Aplicación iniciada.")
    root.mainloop()