import logging
from typing import List, Dict, Optional
from datetime import date
from collections import defaultdict
import math

from src.core.interfaces import BankParserStrategy
from src.core.models import Transaction
from src.services.notion_service import NotionClient
# Categorization logic will be imported here (keeping the old one for now or wrapping it)
# For now, let's assume we reuse categorization.py but moved to src/services or similar.
# Since categorization rules are simple, I'll assume a simple function or import.
from src.services.categorization import load_categorization_rules, categorize_record

logger = logging.getLogger(__name__)

class ProcessorResult:
    def __init__(self):
        self.total_read = 0
        self.successful_inserts = 0
        self.duplicates = 0
        self.errors = []
        self.skipped = 0

    def to_string(self):
        return (f"Leídos: {self.total_read} | Insertados: {self.successful_inserts} | "
                f"Duplicados: {self.duplicates} | Errores: {len(self.errors)}")

class TransactionProcessor:
    def __init__(self, notion_client: NotionClient):
        self.notion = notion_client
        self.categorization_rules = load_categorization_rules() # Loading from existing module

    def process_file(self, file_path: str, parser: BankParserStrategy) -> ProcessorResult:
        result = ProcessorResult()

        # 1. Parse File
        transactions, parse_errors = parser.parse(file_path)
        result.errors.extend(parse_errors)
        result.total_read = len(transactions)

        if not transactions:
            return result

        # 2. Determine Date Range to Query Notion
        min_date = min(t.date for t in transactions)
        max_date = max(t.date for t in transactions)

        # Buffer? Maybe not needed if date range is precise.

        logger.info(f"Consultando Notion entre {min_date} y {max_date}")
        existing_transactions = self.notion.get_transactions_in_range(min_date, max_date)

        # Build index for fast lookup (Date + Account + Amount)
        # Why not name? User said: "en Notion puedo cambiar el nombre del gasto, pero no la cantidad o el banco"
        # So key should be (Date, Account, Amount)
        existing_map = defaultdict(list)
        for t in existing_transactions:
            key = (t.date, t.account, t.amount) # Amount here is signed float
            existing_map[key].append(t)

        # 3. Process Transactions
        for tx in transactions:
            if self._is_duplicate(tx, existing_map):
                result.duplicates += 1
                logger.info(f"Duplicado detectado: {tx}")
            else:
                # Categorize
                # The existing categorization uses 'Nombre' key in a dict.
                # Let's adapt
                subcat_id = categorize_record(tx.description, self.categorization_rules)
                tx.subcategory = subcat_id

                # Upload
                if self.notion.create_transaction(tx):
                    result.successful_inserts += 1
                    logger.info(f"Insertado: {tx}")
                    # Do not add to existing_map here.
                    # We only want to deduplicate against what was ALREADY in DB before this run.
                    # If the file contains 2 identical transactions, and DB has 0, we want to insert both.
                    # (Unless the file has duplicates which are errors, but we assume file lines are valid distinct transactions)
                else:
                    result.errors.append(f"Error subiendo a Notion: {tx.description}")

        return result

    def _is_duplicate(self, tx: Transaction, existing_map: Dict) -> bool:
        key = (tx.date, tx.account, tx.amount)
        if key in existing_map:
            # We found records with same date, account and amount.
            # Is that enough?
            # If I bought 2 coffees for 1.50 same day?
            # The current logic considers it duplicate.
            # "Idempotencia: Revisa la lógica actual para evitar duplicar gastos si proceso el mismo CSV dos veces"
            # If I process the same CSV twice, I want to skip.
            # If I legitimately have two identical transactions in the bank...
            # The bank usually provides balance or ID. We don't have ID.
            # We can't distinguish 2 identical real transactions without bank ID.
            # Assuming if one exists in DB, we skip one from CSV?
            # Or if we have 2 in CSV and 1 in DB, we insert 1?
            # The simple check `if key in existing_map` means if ANY exist, we skip.
            # If I have 2 coffees in CSV, and 0 in DB.
            # 1st coffee: map check -> false. Insert. Add to map.
            # 2nd coffee: map check -> true. Skip. -> ERROR. We skipped the second valid coffee.

            # To fix this, we need to count occurrences.
            # existing_map should map to a COUNT or list of items.
            # I used `defaultdict(list)`.

            # Refined Logic:
            # We need to match CSV transactions 1-to-1 with DB transactions.
            # For this transaction `tx`, do we have an "available" match in `existing_map`?

            candidates = existing_map.get(key, [])
            if candidates:
                # We consume one candidate (mark it as matched)
                candidates.pop(0)
                if not candidates:
                    del existing_map[key]
                return True
            return False

        return False
