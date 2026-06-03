from __future__ import annotations


class Budget:
    """Tracks spending against per-category limits."""

    def __init__(self, categories: dict[str, float]) -> None:
        for name, limit in categories.items():
            if limit <= 0:
                raise ValueError(
                    f"limit for category {name!r} must be positive, got {limit}"
                )
        self._limits: dict[str, float] = {k: float(v) for k, v in categories.items()}
        self._spent: dict[str, float] = {k: 0.0 for k in categories}

    def record_spending(self, category: str, amount: float) -> None:
        if category not in self._limits:
            raise KeyError(f"unknown category: {category!r}")
        if amount <= 0:
            raise ValueError("spending amount must be positive")
        self._spent[category] += amount

    def is_over_budget(self, category: str) -> bool:
        if category not in self._limits:
            raise KeyError(f"unknown category: {category!r}")
        return self._spent[category] > self._limits[category]

    def remaining(self, category: str) -> float:
        if category not in self._limits:
            raise KeyError(f"unknown category: {category!r}")
        return max(0.0, self._limits[category] - self._spent[category])

    def summary(self) -> dict[str, dict[str, float]]:
        return {
            cat: {
                "limit": self._limits[cat],
                "spent": self._spent[cat],
                "remaining": self.remaining(cat),
            }
            for cat in self._limits
        }
