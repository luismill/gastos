import unittest
from unittest.mock import MagicMock, ANY
from datetime import date
import os
import sys

# Add repo root
sys.path.append(os.getcwd())

from src.services.processor import TransactionProcessor
from src.extractors.laboral_kutxa import LaboralKutxaParser
from src.extractors.revolut import RevolutParser
from src.core.models import Transaction

class TestFullFlow(unittest.TestCase):
    def setUp(self):
        self.mock_notion = MagicMock()
        self.processor = TransactionProcessor(self.mock_notion)

    def test_laboral_kutxa_flow(self):
        # Setup Notion mock to return NO existing transactions
        self.mock_notion.get_transactions_in_range.return_value = []
        self.mock_notion.create_transaction.return_value = True

        parser = LaboralKutxaParser()
        result = self.processor.process_file("tests/data/laboral_kutxa.csv", parser)

        print("\nLaboral Kutxa Result:", result.to_string())

        self.assertEqual(result.total_read, 3)
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(result.successful_inserts, 3)

        # Verify notion calls
        self.mock_notion.get_transactions_in_range.assert_called_once()
        self.assertEqual(self.mock_notion.create_transaction.call_count, 3)

    def test_revolut_flow_duplicates(self):
        # Test idempotency

        # Notion already has the Coffee transaction.
        existing_tx = Transaction(
            date=date(2024, 1, 3),
            description="Coffee",
            amount=-3.2,
            account="Revolut"
        )
        self.mock_notion.get_transactions_in_range.return_value = [existing_tx]
        self.mock_notion.create_transaction.return_value = True

        parser = RevolutParser()
        result = self.processor.process_file("tests/data/revolut.csv", parser)

        print("\nRevolut Result:", result.to_string())

        # Revolut dummy file has 4 lines.
        # Line 4 "Corrupt Row" has valid date but NaN amount -> parsed as 0.0 amount. Valid transaction.
        # So 4 transactions read.

        self.assertEqual(result.total_read, 4)
        self.assertEqual(result.duplicates, 1) # Coffee should be duplicate
        self.assertEqual(result.successful_inserts, 3) # Uber, Freelance, Corrupt(0.0)

        # Verify categorisation for Uber (rule exists)
        calls = self.mock_notion.create_transaction.call_args_list
        uber_tx = None
        for call in calls:
            tx = call[0][0] # first arg
            if "Uber" in tx.description:
                uber_tx = tx
                break

        self.assertIsNotNone(uber_tx)
        # Expecting 'uuid-uber' from categorization rules
        self.assertEqual(uber_tx.subcategory, "uuid-uber")

if __name__ == '__main__':
    unittest.main()
