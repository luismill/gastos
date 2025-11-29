from dataclasses import dataclass
from typing import Optional
from datetime import date
from decimal import Decimal

@dataclass
class Transaction:
    date: date
    description: str
    amount: float  # Negative for expense, positive for income
    account: str
    category: Optional[str] = None
    subcategory: Optional[str] = None

    @property
    def is_expense(self) -> bool:
        return self.amount < 0

    @property
    def is_income(self) -> bool:
        return self.amount > 0

    @property
    def abs_amount(self) -> float:
        return abs(self.amount)
