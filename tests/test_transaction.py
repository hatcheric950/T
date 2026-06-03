import pytest
from expensetracker import Transaction


def test_create_credit_transaction():
    t = Transaction(50.0, "credit", "salary")
    assert t.amount == 50.0
    assert t.type_ == "credit"
    assert t.description == "salary"


def test_create_debit_transaction():
    t = Transaction(20.0, "debit", "groceries")
    assert t.amount == 20.0
    assert t.type_ == "debit"


def test_is_credit():
    t = Transaction(100.0, "credit", "bonus")
    assert t.is_credit() is True
    assert t.is_debit() is False


def test_is_debit():
    t = Transaction(15.0, "debit", "coffee")
    assert t.is_debit() is True
    assert t.is_credit() is False


def test_description_is_stripped():
    t = Transaction(10.0, "credit", "  tip  ")
    assert t.description == "tip"


# --- Missing coverage below this line ---
# Not tested:
#   - Transaction(0, "credit", "x") raises ValueError (zero amount)
#   - Transaction(-5, "credit", "x") raises ValueError (negative amount)
#   - Transaction(10, "transfer", "x") raises ValueError (invalid type_)
#   - Transaction(10, "credit", "") raises ValueError (empty description)
#   - Transaction(10, "credit", "   ") raises ValueError (whitespace description)
#   - t.to_dict() returns correct dict structure
#   - t.date defaults to today when not supplied
#   - t.date is stored correctly when supplied explicitly
#   - Transaction.__repr__
