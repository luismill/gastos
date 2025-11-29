import pandas as pd
import logging
from typing import List, Tuple
from datetime import datetime
from src.core.interfaces import BankParserStrategy
from src.core.models import Transaction

class LaboralKutxaParser(BankParserStrategy):
    def parse(self, file_path: str) -> Tuple[List[Transaction], List[str]]:
        transactions = []
        errors = []

        try:
            # Read all as string first to avoid pandas type inference issues initially
            df = pd.read_csv(file_path, delimiter=";", dtype=str)
        except Exception as e:
            return [], [f"Error al leer el archivo CSV: {str(e)}"]

        required_columns = ["Fecha valor", "Concepto", "Importe"]
        if not all(col in df.columns for col in required_columns):
             return [], [f"El archivo no tiene las columnas requeridas: {required_columns}"]

        for index, row in df.iterrows():
            try:
                # 1. Parse Date
                raw_date = row["Fecha valor"]
                if not isinstance(raw_date, str):
                    raise ValueError("Fecha inválida")
                # Handle "01/01/2024" potentially with extra text
                date_str = raw_date.split()[0]
                tx_date = datetime.strptime(date_str, "%d/%m/%Y").date()

                # 2. Parse Amount
                raw_amount = row["Importe"]
                if isinstance(raw_amount, str):
                    # Replace dots with nothing (thousands?) no, usually just replace , with .
                    # Laboral Kutxa usually is 1.000,00 or 1000,00.
                    # Assuming standard Spanish format: . = thousands, , = decimal
                    clean_amount = raw_amount.replace('.', '').replace(',', '.')
                    amount = float(clean_amount)
                else:
                    amount = float(raw_amount)

                # 3. Create Transaction
                transactions.append(Transaction(
                    date=tx_date,
                    description=str(row["Concepto"]),
                    amount=amount,
                    account="Laboral Kutxa"
                ))

            except Exception as e:
                errors.append(f"Fila {index + 2}: Error procesando: {str(e)} | Datos: {row.to_dict()}")

        return transactions, errors
