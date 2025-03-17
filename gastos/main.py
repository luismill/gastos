import pandas as pd
from bank_config import BankConfig
from notion_api import insert_notion_record, read_notion_records, record_exists
import tkinter as tk
from tkinter import filedialog, messagebox

def process_gasto_ingreso(df):
    # Separate Gasto and Ingreso
    df['Gasto'] = df['Gasto/Ingreso'].apply(lambda x: -x if x < 0 else None)
    df['Ingreso'] = df['Gasto/Ingreso'].apply(lambda x: x if x > 0 else None)
    
    # Drop the temporary 'Gasto/Ingreso' column
    df.drop(columns=['Gasto/Ingreso'], inplace=True)
    return df

def read_bank_records(bank_config, filename):
    if bank_config.bank == "Laboral Kutxa":
        df = pd.read_csv(filename, usecols=bank_config.column_names, delimiter=";", decimal=",")
        df['Fecha valor'] = pd.to_datetime(df['Fecha valor'].str.split().str[0], format='%d/%m/%Y', errors='coerce')
        df['Concepto'] = df['Concepto'].astype(str)
        df['Importe'] = df['Importe'].astype(float)
        df['Cuenta'] = "Laboral Kutxa"
        
        # Rename columns to match Notion
        df.rename(columns={
            'Fecha valor': 'Fecha',
            'Concepto': 'Nombre',
            'Importe': 'Gasto/Ingreso'
        }, inplace=True)
        
        df = process_gasto_ingreso(df)
        return df
    elif bank_config.bank == "BBVA":
        try:
            df = pd.read_excel(filename, skiprows=4, usecols=bank_config.column_names)
            df['F.Valor'] = pd.to_datetime(df['F.Valor'], format='%d/%m/%Y', errors='coerce')
            df['Concepto'] = df['Concepto'].astype(str)
            df['Importe'] = df['Importe'].astype(float)
            df['Cuenta'] = "BBVA"
            
            # Rename columns to match Notion
            df.rename(columns={
                'F.Valor': 'Fecha',
                'Concepto': 'Nombre',
                'Importe': 'Gasto/Ingreso'
            }, inplace=True)
            
            df = process_gasto_ingreso(df)
            return df
        except Exception as e:
            print(f"Error reading Excel file: {e}")
            return pd.DataFrame()  # Return an empty DataFrame in case of error
    else:
        raise ValueError("Unsupported bank or file format")

def process_file(bank_name, file_path):
    bank = BankConfig(bank_name)
    data = read_bank_records(bank, file_path)
    
    successful_inserts = {}
    repeated_records = {}

    # Diccionario de subcategorías basado en el nombre
    subcategoria_dict = {
        "PRESTAMO 3634614742": "db27f81e-62df-40a7-b99e-fcecff99fd78",
        "RBO CRUZ ROJA": "be124c3c-09b9-4976-b33c-f0ab61f52ab5",
        "RBO ASOCIACION ESPANOLA CONTRA EL C": "be124c3c-09b9-4976-b33c-f0ab61f52ab5",
        "REPSOL WAYLET": "b527caba-092d-4a6a-b29a-513dc6b20841",
        "Adeudo medicos sin fronteras, espa/a": "be124c3c-09b9-4976-b33c-f0ab61f52ab5"
    }

    # Read existing records from Notion once
    existing_records = read_notion_records()

    if not data.empty:
        for index, record in data.iterrows():
            nombre = record['Nombre']
            fecha = record['Fecha']
            cuenta = record['Cuenta']
            gasto = record['Gasto']
            ingreso = record['Ingreso']
            month = fecha.strftime('%Y-%m') if not pd.isna(fecha) else None

            # Replace NaN values with None
            if pd.isna(gasto):
                gasto = None
            if pd.isna(ingreso):
                ingreso = None

            # Asignar subcategoría basada en el nombre
            subcategoria = subcategoria_dict.get(nombre, None)

            if month and not record_exists(existing_records, fecha.strftime('%Y-%m-%d'), cuenta, gasto, ingreso):
                response = insert_notion_record(nombre, fecha.strftime('%Y-%m-%d'), cuenta, gasto=gasto, ingreso=ingreso, subcategoria=subcategoria)
                if response:
                    successful_inserts[month] = successful_inserts.get(month, 0) + 1
            else:
                if month:
                    repeated_records[month] = repeated_records.get(month, 0) + 1

        print("Successful inserts per month:", successful_inserts)
        print("Repeated records per month:", repeated_records)
    else:
        print("No records found in the file.")

def select_file():
    file_path = filedialog.askopenfilename()
    if file_path:
        bank_name = bank_var.get()
        process_file(bank_name, file_path)
    else:
        messagebox.showwarning("No file selected", "Please select a file to process.")

if __name__ == "__main__":
    root = tk.Tk()
    root.title("Bank Records Processor")
    root.geometry("400x200")  # Set the window size

    tk.Label(root, text="Select Bank:").pack(pady=10)
    bank_var = tk.StringVar(value="BBVA")
    bank_menu = tk.OptionMenu(root, bank_var, "BBVA", "Laboral Kutxa")
    bank_menu.pack(pady=10)

    tk.Button(root, text="Select File", command=select_file).pack(pady=20)

    root.mainloop()