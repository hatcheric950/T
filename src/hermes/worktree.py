from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path


def create_worktree() -> Path:
    """Create a temporary git worktree off the current branch and return its path."""
    repo_root = subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"], text=True
    ).strip()
    branch = subprocess.check_output(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True
    ).strip()
    tmp = Path(tempfile.mkdtemp(prefix="hermes-wt-"))
    new_branch = f"hermes/{branch}-{tmp.name.split('-')[-1]}"
    subprocess.check_call(["git", "worktree", "add", "-b", new_branch, str(tmp)], cwd=repo_root)
    os.chdir(tmp)
    return tmp
