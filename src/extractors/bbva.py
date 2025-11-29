import pandas as pd
import logging
from typing import List, Tuple
from datetime import datetime
from src.core.interfaces import BankParserStrategy
from src.core.models import Transaction

class BBVAParser(BankParserStrategy):
    def parse(self, file_path: str) -> Tuple[List[Transaction], List[str]]:
        transactions = []
        errors = []

        try:
            # BBVA skips 4 rows
            df = pd.read_excel(file_path, skiprows=4, dtype=str)
        except Exception as e:
            return [], [f"Error al leer el archivo Excel: {str(e)}"]

        # Rename columns to normalize access if needed, or just use keys
        # "F.Valor", "Concepto", "Importe", "Observaciones"
        required_columns = ["F.Valor", "Concepto", "Importe"]
        if not all(col in df.columns for col in required_columns):
             # Try to see if columns are slightly different or just warn
             return [], [f"El archivo no tiene las columnas requeridas: {required_columns}. Encontradas: {df.columns.tolist()}"]

        for index, row in df.iterrows():
            try:
                # 1. Parse Date "01/01/2024"
                raw_date = row["F.Valor"]
                if not isinstance(raw_date, str):
                    # Sometimes excel reads as datetime already
                    if isinstance(raw_date, datetime):
                        tx_date = raw_date.date()
                    else:
                        raise ValueError(f"Formato de fecha desconocido: {raw_date}")
                else:
                    tx_date = datetime.strptime(raw_date, "%d/%m/%Y").date()

                # 2. Parse Amount
                raw_amount = row["Importe"]
                if isinstance(raw_amount, (int, float)):
                    amount = float(raw_amount)
                else:
                    clean_amount = str(raw_amount).replace('.', '').replace(',', '.')
                    amount = float(clean_amount)

                # 3. Description Logic
                nombre = str(row["Concepto"])
                observaciones = str(row["Observaciones"]) if "Observaciones" in row and pd.notna(row["Observaciones"]) else ""

                description = nombre
                if "transferencia" in nombre.lower():
                    description = f"Transferencia: {observaciones}"
                elif "bizum" in nombre.lower():
                    description = f"Bizum: {observaciones}"

                transactions.append(Transaction(
                    date=tx_date,
                    description=description,
                    amount=amount,
                    account="BBVA"
                ))
            except Exception as e:
                errors.append(f"Fila {index + 6}: Error procesando: {str(e)} | Datos: {row.to_dict()}") # +6 because 4 skipped + 1 header + 0-index

        return transactions, errors
