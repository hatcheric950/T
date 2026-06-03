import pytest
from expensetracker import Account


def test_create_account():
    acc = Account("Alice", 100.0)
    assert acc.owner == "Alice"
    assert acc.get_balance() == 100.0


def test_create_account_default_balance():
    acc = Account("Bob")
    assert acc.get_balance() == 0.0


def test_deposit_increases_balance():
    acc = Account("Alice", 50.0)
    acc.deposit(25.0)
    assert acc.get_balance() == 75.0


def test_withdraw_decreases_balance():
    acc = Account("Alice", 100.0)
    acc.withdraw(40.0)
    assert acc.get_balance() == 60.0


def test_multiple_operations():
    acc = Account("Alice", 200.0)
    acc.deposit(50.0)
    acc.withdraw(30.0)
    assert acc.get_balance() == 220.0


# --- Missing coverage below this line ---
# Not tested:
#   - Account("") raises ValueError (empty owner)
#   - Account("Alice", -1) raises ValueError (negative initial balance)
#   - acc.deposit(0) raises ValueError
#   - acc.deposit(-5) raises ValueError
#   - acc.withdraw(0) raises ValueError
#   - acc.withdraw(-5) raises ValueError
#   - acc.withdraw(amount > balance) raises ValueError (overdraft)
#   - acc.get_history() returns correct Transaction records
#   - Account.__repr__
