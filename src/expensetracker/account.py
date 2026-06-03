from __future__ import annotations
from .transaction import Transaction


class Account:
    def __init__(self, owner: str, initial_balance: float = 0.0) -> None:
        if not owner or not owner.strip():
            raise ValueError("owner must be a non-empty string")
        if initial_balance < 0:
            raise ValueError("initial_balance cannot be negative")
        self.owner = owner.strip()
        self._balance = float(initial_balance)
        self._history: list[Transaction] = []

    def deposit(self, amount: float) -> None:
        if amount <= 0:
            raise ValueError("deposit amount must be positive")
        self._balance += amount
        self._history.append(Transaction(amount, "credit", "deposit"))

    def withdraw(self, amount: float) -> None:
        if amount <= 0:
            raise ValueError("withdrawal amount must be positive")
        if amount > self._balance:
            raise ValueError(
                f"insufficient funds: balance is {self._balance:.2f}, "
                f"requested {amount:.2f}"
            )
        self._balance -= amount
        self._history.append(Transaction(amount, "debit", "withdrawal"))

    def get_balance(self) -> float:
        return self._balance

    def get_history(self) -> list[Transaction]:
        return list(self._history)

    def __repr__(self) -> str:
        return f"Account(owner={self.owner!r}, balance={self._balance:.2f})"
