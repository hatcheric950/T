# expensetracker

A small Python library for tracking expenses, budgets, and account balances.
This project demonstrates test coverage analysis.

## Setup

```bash
pip install -e ".[dev]"
```

## Run tests with coverage

```bash
python -m pytest tests/ --cov=src/expensetracker --cov-report=term-missing -v
```

## Project structure

```
src/expensetracker/
  account.py      # Account class — balance, deposit, withdraw, history
  transaction.py  # Transaction class — amount, type, description, date
  budget.py       # Budget class — per-category limits and overspend detection
  utils.py        # Helpers — currency formatting, date parsing, validation

tests/
  test_account.py     # Partial coverage of Account (happy paths only)
  test_transaction.py # Partial coverage of Transaction (happy paths only)
```

## Coverage status

| Module         | Coverage | Gap                                       |
|----------------|----------|-------------------------------------------|
| account.py     | ~69%     | Error paths, history tracking, `__repr__` |
| transaction.py | ~73%     | Validation errors, `to_dict`, `__repr__`  |
| budget.py      | ~19%     | Entire module nearly untested             |
| utils.py       | ~26%     | Entire module nearly untested             |

See [COVERAGE_ANALYSIS.md](COVERAGE_ANALYSIS.md) for the full improvement proposal.
