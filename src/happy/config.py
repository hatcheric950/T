import json
import os
from pathlib import Path

CONFIG_DIR = Path.home() / ".happy"
CONFIG_FILE = CONFIG_DIR / "config.json"


def load() -> dict:
    if CONFIG_FILE.exists():
        with CONFIG_FILE.open() as f:
            return json.load(f)
    return {}


def save(data: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with CONFIG_FILE.open("w") as f:
        json.dump(data, f, indent=2)
    CONFIG_FILE.chmod(0o600)


def get_provider(name: str) -> dict | None:
    return load().get("providers", {}).get(name.lower())
