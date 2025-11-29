from abc import ABC, abstractmethod
from typing import List, Tuple
from src.core.models import Transaction

class BankParserStrategy(ABC):
    @abstractmethod
    def parse(self, file_path: str) -> Tuple[List[Transaction], List[str]]:
        """
        Parses a bank file.
        Returns a tuple: (list of valid Transactions, list of error messages)
        """
        pass
