import pandas as pd
import logging
from typing import List, Tuple
from datetime import datetime
from src.core.interfaces import BankParserStrategy
from src.core.models import Transaction

class RevolutParser(BankParserStrategy):
    def parse(self, file_path: str) -> Tuple[List[Transaction], List[str]]:
        transactions = []
        errors = []

        try:
            df = pd.read_csv(file_path, delimiter=",", dtype=str)
        except Exception as e:
            return [], [f"Error al leer el archivo CSV: {str(e)}"]

        required_columns = ["Fecha de inicio", "Descripción", "Importe", "Comisión"]
        if not all(col in df.columns for col in required_columns):
             return [], [f"El archivo no tiene las columnas requeridas: {required_columns}"]

        for index, row in df.iterrows():
            try:
                # 1. Parse Date "2024-01-01 10:00:00"
                raw_date = row["Fecha de inicio"]
                if not isinstance(raw_date, str):
                    raise ValueError("Fecha inválida")
                tx_date = datetime.strptime(raw_date, "%Y-%m-%d %H:%M:%S").date()

                # 2. Parse Amount & Commission
                def parse_float(val):
                    if pd.isna(val) or val == "":
                        return 0.0
                    val = str(val).strip()
                    val = val.replace('€', '').replace(' ', '')
                    # Revolut CSV usually uses dot for decimal? or depends on locale?
                    # Original code: if ',' in value: value = value.replace('.', '').replace(',', '.')
                    # Let's assume standard logic:
                    # If ',' is present and '.' is present, and '.' < ',', then . is thousand, , is decimal
                    # Simplification from original code:
                    if ',' in val:
                         val = val.replace('.', '').replace(',', '.')
                    return float(val)

                amount = parse_float(row["Importe"])
                commission = parse_float(row["Comisión"])
                total_amount = amount - commission

                # 3. Create Transaction
                transactions.append(Transaction(
                    date=tx_date,
                    description=str(row["Descripción"]),
                    amount=total_amount,
                    account="Revolut"
                ))
            except Exception as e:
                errors.append(f"Fila {index + 2}: Error procesando: {str(e)} | Datos: {row.to_dict()}")

        return transactions, errors
