from __future__ import annotations
from datetime import date as date_type
from typing import Any


VALID_TYPES = {"credit", "debit"}


class Transaction:
    def __init__(
        self,
        amount: float,
        type_: str,
        description: str,
        date: date_type | None = None,
    ) -> None:
        if amount <= 0:
            raise ValueError("amount must be positive")
        if type_ not in VALID_TYPES:
            raise ValueError(f"type_ must be one of {VALID_TYPES!r}, got {type_!r}")
        if not description or not description.strip():
            raise ValueError("description must be a non-empty string")
        self.amount = float(amount)
        self.type_ = type_
        self.description = description.strip()
        self.date = date if date is not None else date_type.today()

    def is_debit(self) -> bool:
        return self.type_ == "debit"

    def is_credit(self) -> bool:
        return self.type_ == "credit"

    def to_dict(self) -> dict[str, Any]:
        return {
            "amount": self.amount,
            "type": self.type_,
            "description": self.description,
            "date": self.date.isoformat(),
        }

    def __repr__(self) -> str:
        return (
            f"Transaction(amount={self.amount:.2f}, type={self.type_!r}, "
            f"description={self.description!r}, date={self.date})"
        )
