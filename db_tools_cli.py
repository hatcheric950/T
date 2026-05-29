#!/usr/bin/env python3
"""
db_tools_cli.py — CLI for the Database Migration Generator and ER Diagram Generator.

Usage examples
--------------
  # Generate Flyway migration script
  python db_tools_cli.py migrate --old examples/entities/User_v1.java \
                                  --new examples/entities/User_v2.java

  # Generate Mermaid ER diagram
  python db_tools_cli.py er --sql examples/schema.sql

  # Write output to a file
  python db_tools_cli.py er --sql examples/schema.sql --output diagram.md
"""
import argparse
import sys
from pathlib import Path

from db_tools import generate_migration, generate_mermaid_er, parse_sql_schema


def cmd_migrate(args: argparse.Namespace) -> None:
    old_path = Path(args.old)
    new_path = Path(args.new)

    if not old_path.exists():
        sys.exit(f"Error: file not found: {old_path}")
    if not new_path.exists():
        sys.exit(f"Error: file not found: {new_path}")

    old_source = old_path.read_text(encoding="utf-8")
    new_source = new_path.read_text(encoding="utf-8")
    result = generate_migration(old_source, new_source, version=args.version)

    if args.output:
        Path(args.output).write_text(result, encoding="utf-8")
        print(f"Migration script written to {args.output}")
    else:
        print(result)


def cmd_er(args: argparse.Namespace) -> None:
    sql_path = Path(args.sql)
    if not sql_path.exists():
        sys.exit(f"Error: file not found: {sql_path}")

    sql = sql_path.read_text(encoding="utf-8")
    tables = parse_sql_schema(sql)
    if not tables:
        sys.exit("No CREATE TABLE statements found in the provided SQL file.")

    result = generate_mermaid_er(tables)

    if args.output:
        out = Path(args.output)
        content = f"```mermaid\n{result}```\n"
        out.write_text(content, encoding="utf-8")
        print(f"ER diagram written to {args.output}")
    else:
        print(result)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="db_tools_cli",
        description="Database tooling: Flyway migration generator & Mermaid ER diagram generator",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # --- migrate sub-command ---
    m = sub.add_parser(
        "migrate",
        help="Compare two JPA entity versions and generate a Flyway migration script",
    )
    m.add_argument("--old", required=True, metavar="FILE", help="Previous entity Java file")
    m.add_argument("--new", required=True, metavar="FILE", help="Current entity Java file")
    m.add_argument(
        "--version",
        default=None,
        metavar="VERSION",
        help="Flyway version string (default: current timestamp)",
    )
    m.add_argument("--output", default=None, metavar="FILE", help="Write SQL to file")
    m.set_defaults(func=cmd_migrate)

    # --- er sub-command ---
    e = sub.add_parser(
        "er",
        help="Parse a SQL schema file and generate a Mermaid ER diagram",
    )
    e.add_argument("--sql", required=True, metavar="FILE", help="SQL schema file")
    e.add_argument(
        "--output",
        default=None,
        metavar="FILE",
        help="Write Mermaid diagram to Markdown file",
    )
    e.set_defaults(func=cmd_er)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
