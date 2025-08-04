import pandas as pd
import logging
from tkinter import messagebox

def process_gasto_ingreso(df):
    df['Gasto'] = df['Gasto/Ingreso'].apply(lambda x: -x if x < 0 else None)
    df['Ingreso'] = df['Gasto/Ingreso'].apply(lambda x: x if x > 0 else None)
    df.drop(columns=['Gasto/Ingreso'], inplace=True)
    return df

def read_bank_records(bank_config, filename):
    logging.info(f"Leyendo archivo bancario: {filename} para banco: {bank_config.bank}")
    if bank_config.bank == "Laboral Kutxa":
        df = pd.read_csv(filename, usecols=bank_config.column_names, delimiter=";", decimal=",")
        df['Fecha valor'] = pd.to_datetime(df['Fecha valor'].str.split().str[0], format='%d/%m/%Y', errors='coerce')
        df['Concepto'] = df['Concepto'].astype(str)
        df['Importe'] = df['Importe'].astype(float)
        df['Cuenta'] = "Laboral Kutxa"
        df.rename(columns={
            'Fecha valor': 'Fecha',
            'Concepto': 'Nombre',
            'Importe': 'Gasto/Ingreso'
        }, inplace=True)
        df = process_gasto_ingreso(df)
        logging.info(f"Archivo de Laboral Kutxa leído correctamente con {len(df)} registros.")
        return df
    elif bank_config.bank == "Revolut":
        df = pd.read_csv(filename, usecols=bank_config.column_names, delimiter=",")
        df['Started Date'] = pd.to_datetime(df['Started Date'], format='%Y-%m-%d %H:%M:%S', errors='coerce').dt.date
        df['Description'] = df['Description'].astype(str)
        df['Amount'] = df['Amount'].astype(float) - df['Fee'].astype(float)
        df['Cuenta'] = "Revolut"
        df.rename(columns={
            'Started Date': 'Fecha',
            'Description': 'Nombre',
            'Amount': 'Gasto/Ingreso'
        }, inplace=True)
        df = process_gasto_ingreso(df)
        logging.info(f"Archivo de Revolut leído correctamente con {len(df)} registros.")
        return df
    elif bank_config.bank == "BBVA":
        try:
            df = pd.read_excel(filename, skiprows=4, usecols=bank_config.column_names)
            df['F.Valor'] = pd.to_datetime(df['F.Valor'], format='%d/%m/%Y', errors='coerce')
            df['Concepto'] = df['Concepto'].astype(str)
            df['Importe'] = df['Importe'].astype(float)
            df['Cuenta'] = "BBVA"
            df.rename(columns={
                'F.Valor': 'Fecha',
                'Concepto': 'Nombre',
                'Importe': 'Gasto/Ingreso'
            }, inplace=True)
            if 'Observaciones' in df.columns:
                def custom_nombre(row):
                    concepto = row['Nombre'].lower()
                    if "transferencia" in concepto:
                        return f"Transferencia: {row['Observaciones']}"
                    elif "bizum" in concepto:
                        return f"Bizum: {row['Observaciones']}"
                    else:
                        return row['Nombre']
                df['Nombre'] = df.apply(custom_nombre, axis=1)
            df = process_gasto_ingreso(df)
            logging.info(f"Archivo de BBVA leído correctamente con {len(df)} registros.")
            return df
        except Exception as e:
            logging.error(f"Error leyendo archivo Excel: {e}")
            messagebox.showerror("Error", f"Error leyendo archivo Excel: {e}")
            return pd.DataFrame()
    else:
        logging.error("Banco o formato de archivo no soportado")
        messagebox.showerror("Error", f"Banco o formato de archivo no soportado: {bank_config.bank}")
        return None