from __future__ import annotations

import argparse
import sys
from typing import Sequence

from rich.console import Console
from rich.markdown import Markdown

from . import __version__
from .agent import Agent
from .config import Config, DEFAULT_MODEL, DEFAULT_TOOLSETS
from .session import Session
from .worktree import create_worktree


console = Console()


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="hermes", description="Hermes CLI agent")
    p.add_argument("--version", action="version", version=f"hermes {__version__}")
    _add_shared_flags(p)
    p.add_argument("-c", "--continue", dest="cont", action="store_true",
                   help="Resume the most recent CLI session")
    p.add_argument("-r", "--resume", metavar="SESSION_ID",
                   help="Resume a specific session by ID")
    p.add_argument("-w", "--worktree", action="store_true",
                   help="Run in an isolated git worktree")

    sub = p.add_subparsers(dest="command")
    chat = sub.add_parser("chat", help="Chat mode (default if -q is given)")
    _add_shared_flags(chat)
    chat.add_argument("-q", "--query", help="Run a single query and exit")
    chat.add_argument("-c", "--continue", dest="cont", action="store_true")
    chat.add_argument("-r", "--resume", metavar="SESSION_ID")
    chat.add_argument("-w", "--worktree", action="store_true")
    return p


def _add_shared_flags(p: argparse.ArgumentParser) -> None:
    p.add_argument("--model", default=DEFAULT_MODEL, help="Model identifier")
    p.add_argument("--provider", choices=["anthropic", "openrouter", "nous"],
                   help="Force a provider (else inferred from model prefix)")
    p.add_argument("--toolsets", default=",".join(DEFAULT_TOOLSETS),
                   help="Comma-separated toolsets to enable")
    p.add_argument("-s", "--skills", default="",
                   help="Comma-separated skills to preload")
    p.add_argument("--verbose", action="store_true", help="Verbose/debug output")


def _config_from_args(args: argparse.Namespace) -> Config:
    return Config(
        model=args.model,
        provider=args.provider,
        toolsets=tuple(t.strip() for t in args.toolsets.split(",") if t.strip()),
        skills=tuple(s.strip() for s in args.skills.split(",") if s.strip()),
        verbose=args.verbose,
    )


def _resolve_session(args: argparse.Namespace, cfg: Config) -> Session | None:
    if getattr(args, "resume", None):
        return Session.load(args.resume)
    if getattr(args, "cont", False):
        s = Session.most_recent()
        if s is None and cfg.verbose:
            console.print("[yellow]No prior session found; starting fresh.[/yellow]")
        return s
    return None


def _run_single(agent: Agent, query: str) -> int:
    try:
        reply = agent.send(query)
    except Exception as e:
        console.print(f"[red]error:[/red] {e}")
        return 1
    console.print(Markdown(reply))
    console.print(f"\n[dim]session: {agent.session.id}[/dim]")
    return 0


def _run_interactive(agent: Agent) -> int:
    console.print(f"[bold]hermes[/bold] · {agent.config.model} "
                  f"({agent.config.resolve_provider()}) · session {agent.session.id}")
    console.print("Type /exit to quit, /reset to start a new session.")
    while True:
        try:
            line = input("› ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print()
            return 0
        if not line:
            continue
        if line in {"/exit", "/quit"}:
            return 0
        if line == "/reset":
            agent.session = Session.new(agent.config.model, agent.config.resolve_provider())
            console.print(f"[dim]new session: {agent.session.id}[/dim]")
            continue
        try:
            reply = agent.send(line)
        except Exception as e:
            console.print(f"[red]error:[/red] {e}")
            continue
        console.print(Markdown(reply))


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if getattr(args, "worktree", False):
        path = create_worktree()
        if args.verbose:
            console.print(f"[dim]worktree: {path}[/dim]")

    cfg = _config_from_args(args)
    session = _resolve_session(args, cfg)
    agent = Agent.start(cfg, session)

    query = getattr(args, "query", None)
    if query:
        return _run_single(agent, query)
    return _run_interactive(agent)


if __name__ == "__main__":
    sys.exit(main())
