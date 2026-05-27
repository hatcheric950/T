"""happy — CLI entrypoint."""

from __future__ import annotations

import argparse
import sys

from . import __version__
from . import connect as connect_mod
from . import env as env_mod


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="happy",
        description="Manage AI provider connections.",
    )
    parser.add_argument(
        "--version", action="version", version=f"happy {__version__}"
    )

    sub = parser.add_subparsers(dest="command", metavar="<command>")

    connect_p = sub.add_parser(
        "connect",
        help="Connect to an AI provider (e.g. Claude).",
    )
    connect_p.add_argument(
        "provider",
        metavar="PROVIDER",
        help="Provider name, e.g. Claude",
    )

    return parser


def main(argv: list[str] | None = None) -> None:
    env_mod.load_dotenv_files()
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "connect":
        connect_mod.run(args.provider)
    else:
        parser.print_help()
        sys.exit(1)
