# Test Coverage Analysis

Running `python -m pytest tests/ --cov=src/expensetracker --cov-report=term-missing -v`
produces this baseline (branch coverage enabled):

| Module                     | Stmts | Miss | Branch | BrPart | Cover | Missing lines          |
|----------------------------|-------|------|--------|--------|-------|------------------------|
| `__init__.py`              | 5     | 0    | 0      | 0      | 100%  | —                      |
| `account.py`               | 29    | 7    | 10     | 5      | 69%   | 8, 10, 17, 23, 25, 36, 39 |
| `budget.py`                | 24    | 17   | 12     | 0      | 19%   | 8–14, 17–21, 24–26, 29–31, 34 |
| `transaction.py`           | 24    | 5    | 6      | 3      | 73%   | 18, 20, 22, 35, 43     |
| `utils.py`                 | 23    | 15   | 8      | 0      | 26%   | 11–13, 18–25, 32–33, 38–39 |
| **TOTAL**                  | 105   | 44   | 36     | 8      | **49%** |                      |

10 tests pass; overall coverage is 49%.

---

## Proposed improvements

### 1  `account.py` — cover error paths and history (69% → ~95%)

The existing tests only exercise the happy path. The following cases are untested:

| Scenario | Why it matters |
|---|---|
| `Account("", 100)` → `ValueError` | Guards against anonymous accounts silently being created |
| `Account("Alice", -50)` → `ValueError` | A negative starting balance is a data-integrity bug |
| `acc.deposit(0)` and `acc.deposit(-5)` → `ValueError` | Zero/negative deposits silently corrupt the balance |
| `acc.withdraw(0)` and `acc.withdraw(-5)` → `ValueError` | Same as above for withdrawals |
| `acc.withdraw(1000)` on a $100 account → `ValueError` | The overdraft guard is the most financially critical path |
| `acc.get_history()` after deposits/withdrawals | Verifies the audit trail is built correctly |
| `repr(acc)` | Smoke-tests the string representation doesn't crash |

**Suggested test file additions** — `tests/test_account.py`:

```python
def test_empty_owner_raises():
    with pytest.raises(ValueError, match="non-empty"):
        Account("")

def test_negative_initial_balance_raises():
    with pytest.raises(ValueError, match="negative"):
        Account("Alice", -1)

def test_deposit_zero_raises():
    acc = Account("Alice", 100)
    with pytest.raises(ValueError, match="positive"):
        acc.deposit(0)

def test_deposit_negative_raises():
    acc = Account("Alice", 100)
    with pytest.raises(ValueError, match="positive"):
        acc.deposit(-10)

def test_withdraw_zero_raises():
    acc = Account("Alice", 100)
    with pytest.raises(ValueError, match="positive"):
        acc.withdraw(0)

def test_withdraw_negative_raises():
    acc = Account("Alice", 100)
    with pytest.raises(ValueError, match="positive"):
        acc.withdraw(-5)

def test_overdraft_raises():
    acc = Account("Alice", 50)
    with pytest.raises(ValueError, match="insufficient funds"):
        acc.withdraw(100)

def test_history_records_transactions():
    acc = Account("Alice", 100)
    acc.deposit(50)
    acc.withdraw(20)
    history = acc.get_history()
    assert len(history) == 2
    assert history[0].is_credit()
    assert history[1].is_debit()

def test_repr():
    acc = Account("Alice", 75)
    assert "Alice" in repr(acc)
    assert "75.00" in repr(acc)
```

---

### 2  `transaction.py` — cover validation and serialisation (73% → ~95%)

The tests confirm basic creation and `is_debit`/`is_credit`, but miss all guard clauses
and the serialisation method.

| Scenario | Why it matters |
|---|---|
| `Transaction(0, "credit", "x")` → `ValueError` | Zero-value transactions should never be stored |
| `Transaction(-5, "credit", "x")` → `ValueError` | Negative amounts circumvent the debit/credit model |
| `Transaction(10, "transfer", "x")` → `ValueError` | An invalid type_ silently corrupts accounting logic |
| `Transaction(10, "credit", "")` → `ValueError` | Empty descriptions make the audit trail useless |
| `t.to_dict()` structure | The dict is likely serialised to JSON/DB; shape must be stable |
| `t.date` defaults to today | Documents the implied contract callers rely on |
| `repr(t)` | Smoke-test |

**Suggested additions** — `tests/test_transaction.py`:

```python
from datetime import date

def test_zero_amount_raises():
    with pytest.raises(ValueError, match="positive"):
        Transaction(0, "credit", "x")

def test_negative_amount_raises():
    with pytest.raises(ValueError, match="positive"):
        Transaction(-1, "debit", "x")

def test_invalid_type_raises():
    with pytest.raises(ValueError, match="type_"):
        Transaction(10, "transfer", "x")

def test_empty_description_raises():
    with pytest.raises(ValueError, match="non-empty"):
        Transaction(10, "credit", "")

def test_whitespace_description_raises():
    with pytest.raises(ValueError, match="non-empty"):
        Transaction(10, "credit", "   ")

def test_to_dict():
    d = date(2024, 1, 15)
    t = Transaction(42.5, "debit", "lunch", d)
    assert t.to_dict() == {
        "amount": 42.5,
        "type": "debit",
        "description": "lunch",
        "date": "2024-01-15",
    }

def test_default_date_is_today():
    t = Transaction(10, "credit", "bonus")
    assert t.date == date.today()

def test_explicit_date_stored():
    d = date(2023, 6, 1)
    t = Transaction(5, "debit", "coffee", d)
    assert t.date == d

def test_repr():
    t = Transaction(10, "credit", "tip")
    assert "credit" in repr(t)
    assert "tip" in repr(t)
```

---

### 3  `budget.py` — add a new test file (19% → ~95%)

`budget.py` has no test file at all. It contains the most business-critical logic:
category limits, overspend detection, and the summary view.

**Create `tests/test_budget.py`**:

```python
import pytest
from expensetracker import Budget


@pytest.fixture
def budget():
    return Budget({"food": 300.0, "transport": 100.0})


def test_initial_remaining_equals_limit(budget):
    assert budget.remaining("food") == 300.0

def test_record_spending_reduces_remaining(budget):
    budget.record_spending("food", 50)
    assert budget.remaining("food") == 250.0

def test_not_over_budget_initially(budget):
    assert budget.is_over_budget("food") is False

def test_over_budget_after_excess_spending(budget):
    budget.record_spending("food", 350)
    assert budget.is_over_budget("food") is True

def test_remaining_floors_at_zero_when_over(budget):
    budget.record_spending("food", 400)
    assert budget.remaining("food") == 0.0

def test_summary_structure(budget):
    budget.record_spending("food", 120)
    s = budget.summary()
    assert s["food"]["limit"] == 300.0
    assert s["food"]["spent"] == 120.0
    assert s["food"]["remaining"] == 180.0
    assert "transport" in s

def test_unknown_category_record_raises(budget):
    with pytest.raises(KeyError, match="unknown category"):
        budget.record_spending("entertainment", 10)

def test_unknown_category_over_budget_raises(budget):
    with pytest.raises(KeyError, match="unknown category"):
        budget.is_over_budget("entertainment")

def test_unknown_category_remaining_raises(budget):
    with pytest.raises(KeyError, match="unknown category"):
        budget.remaining("entertainment")

def test_negative_spending_raises(budget):
    with pytest.raises(ValueError, match="positive"):
        budget.record_spending("food", -10)

def test_zero_spending_raises(budget):
    with pytest.raises(ValueError, match="positive"):
        budget.record_spending("food", 0)

def test_non_positive_limit_raises():
    with pytest.raises(ValueError, match="positive"):
        Budget({"food": 0})
```

---

### 4  `utils.py` — add a new test file (26% → ~95%)

`utils.py` is also completely untested. These helpers are likely called throughout
the application, so bugs here surface as mysterious formatting or parsing errors.

**Create `tests/test_utils.py`**:

```python
import pytest
from datetime import date
from expensetracker.utils import format_currency, parse_date, validate_positive


class TestFormatCurrency:
    def test_basic(self):
        assert format_currency(1234.56) == "$1,234.56"

    def test_custom_symbol(self):
        assert format_currency(50.0, "€") == "€50.00"

    def test_zero(self):
        assert format_currency(0) == "$0.00"

    def test_large_number(self):
        assert format_currency(1_000_000) == "$1,000,000.00"

    def test_non_number_raises():
        with pytest.raises(TypeError):
            format_currency("fifty")


class TestParseDate:
    def test_iso_format(self):
        assert parse_date("2024-03-15") == date(2024, 3, 15)

    def test_slash_dmy(self):
        assert parse_date("15/03/2024") == date(2024, 3, 15)

    def test_slash_mdy(self):
        assert parse_date("03/15/2024") == date(2024, 3, 15)

    def test_dash_dmy(self):
        assert parse_date("15-03-2024") == date(2024, 3, 15)

    def test_invalid_string_raises(self):
        with pytest.raises(ValueError, match="does not match"):
            parse_date("not-a-date")

    def test_non_string_raises(self):
        with pytest.raises(TypeError):
            parse_date(20240315)


class TestValidatePositive:
    def test_positive_passes(self):
        validate_positive(1, "amount")  # no exception

    def test_zero_raises(self):
        with pytest.raises(ValueError, match="amount"):
            validate_positive(0, "amount")

    def test_negative_raises(self):
        with pytest.raises(ValueError, match="count"):
            validate_positive(-3, "count")
```

---

## Priority order

| Priority | Module | Reason |
|---|---|---|
| **High** | `budget.py` | 0 tests; core business logic with financial implications |
| **High** | `account.py` error paths | Overdraft/invalid-deposit bugs are data-integrity issues |
| **Medium** | `utils.py` | Shared helpers; bugs surface everywhere, hard to trace |
| **Medium** | `transaction.py` validation | Input guards protect the entire object model |
