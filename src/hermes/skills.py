from __future__ import annotations

from pathlib import Path

from .config import SKILLS_DIR, ensure_dirs


def load_skills(names: list[str]) -> str:
    """Load skill markdown files and concatenate them as additional system context."""
    ensure_dirs()
    chunks: list[str] = []
    for name in names:
        path = _resolve_skill_path(name)
        if path is None:
            chunks.append(f"# Skill: {name}\n(not found)\n")
            continue
        chunks.append(f"# Skill: {name}\n{path.read_text()}\n")
    return "\n\n".join(chunks)


def _resolve_skill_path(name: str) -> Path | None:
    candidates = [
        SKILLS_DIR / f"{name}.md",
        SKILLS_DIR / name / "SKILL.md",
        SKILLS_DIR / name / "skill.md",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None
