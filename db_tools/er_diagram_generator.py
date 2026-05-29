"""
Mermaid ER diagram generator.

Parses SQL CREATE TABLE statements and produces an erDiagram block
suitable for rendering in Mermaid-compatible tools (GitHub Markdown,
MkDocs, etc.).
"""
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class Column:
    name: str
    data_type: str
    is_primary_key: bool = False
    is_foreign_key: bool = False
    is_not_null: bool = False
    is_unique: bool = False
    references_table: Optional[str] = None
    references_column: Optional[str] = None


@dataclass
class Table:
    name: str
    columns: List[Column] = field(default_factory=list)


def _strip_quotes(s: str) -> str:
    return s.strip().strip("`\"[]'")


def _normalize_type(raw: str) -> str:
    """Return the SQL base type in upper case, without size/precision."""
    return re.sub(r"\s*\(.*?\)", "", raw).strip().upper()


def _split_columns(body: str) -> List[str]:
    """Split a CREATE TABLE body by commas, respecting nested parentheses."""
    parts: List[str] = []
    depth = 0
    buf: List[str] = []
    for ch in body:
        if ch == "(":
            depth += 1
            buf.append(ch)
        elif ch == ")":
            depth -= 1
            buf.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    if buf:
        parts.append("".join(buf))
    return parts


def parse_sql_schema(sql: str) -> List[Table]:
    """
    Parse all CREATE TABLE statements from a SQL string.

    Handles:
    - MySQL / PostgreSQL / SQLite syntax
    - Backtick, double-quote, and bracket-quoted identifiers
    - Table-level PRIMARY KEY, UNIQUE KEY, and FOREIGN KEY constraints
    - Inline column-level PRIMARY KEY, NOT NULL, UNIQUE, REFERENCES
    """
    tables: List[Table] = []

    create_re = re.compile(
        r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?"
        r"[`\"\[]?(\w+)[`\"\]]?"
        r"\s*\((.*?)\)\s*(?:ENGINE|DEFAULT|CHARSET|COMMENT|;|$)",
        re.IGNORECASE | re.DOTALL,
    )

    for m in create_re.finditer(sql):
        table_name = m.group(1)
        body = m.group(2)
        table = Table(name=table_name)

        # --- collect table-level constraints first ---
        primary_keys: set = set()
        pk_re = re.compile(
            r"(?:CONSTRAINT\s+\w+\s+)?PRIMARY\s+KEY\s*\(([^)]+)\)", re.IGNORECASE
        )
        for pk_m in pk_re.finditer(body):
            for k in pk_m.group(1).split(","):
                primary_keys.add(_strip_quotes(k))

        foreign_keys: Dict[str, Tuple[str, str]] = {}
        fk_re = re.compile(
            r"(?:CONSTRAINT\s+\w+\s+)?FOREIGN\s+KEY\s*\(([^)]+)\)"
            r"\s*REFERENCES\s+[`\"\[]?(\w+)[`\"\]]?\s*\(([^)]+)\)",
            re.IGNORECASE,
        )
        for fk_m in fk_re.finditer(body):
            col = _strip_quotes(fk_m.group(1).split(",")[0])
            ref_table = fk_m.group(2)
            ref_col = _strip_quotes(fk_m.group(3).split(",")[0])
            foreign_keys[col] = (ref_table, ref_col)

        unique_cols: set = set()
        uq_re = re.compile(
            r"(?:UNIQUE\s+(?:KEY|INDEX)\s+\w+\s*\(([^)]+)\)"
            r"|CONSTRAINT\s+\w+\s+UNIQUE\s*\(([^)]+)\))",
            re.IGNORECASE,
        )
        for uq_m in uq_re.finditer(body):
            cols_str = uq_m.group(1) or uq_m.group(2)
            for c in cols_str.split(","):
                unique_cols.add(_strip_quotes(c))

        # --- parse individual column lines ---
        skip_re = re.compile(
            r"^\s*(?:PRIMARY|FOREIGN|UNIQUE|KEY|INDEX|CONSTRAINT|CHECK)\b",
            re.IGNORECASE,
        )
        col_re = re.compile(
            r"^\s*[`\"'\[]?(\w+)[`\"'\]]?\s+"   # column name (optionally quoted)
            r"(\w+(?:\s*\([^)]*\))?)"            # type with optional size/precision
            r"(?:\s+.*)?$",                       # rest of constraint keywords
            re.IGNORECASE,
        )

        for line in _split_columns(body):
            line = line.strip()
            if not line or skip_re.match(line):
                continue

            cm = col_re.match(line)
            if not cm:
                continue

            col_name = cm.group(1)
            raw_type = cm.group(2).strip()

            if col_name.upper() in (
                "PRIMARY", "FOREIGN", "UNIQUE", "KEY", "INDEX",
                "CONSTRAINT", "CHECK", "ENGINE", "DEFAULT", "CHARSET",
            ):
                continue

            data_type = _normalize_type(raw_type)
            if not data_type:
                continue

            is_pk = (
                col_name in primary_keys
                or bool(re.search(r"\bPRIMARY\s+KEY\b", line, re.IGNORECASE))
            )
            is_not_null = is_pk or bool(re.search(r"\bNOT\s+NULL\b", line, re.IGNORECASE))
            is_unique = (
                is_pk
                or col_name in unique_cols
                or bool(re.search(r"\bUNIQUE\b", line, re.IGNORECASE))
            )

            ref_table: Optional[str] = None
            ref_col: Optional[str] = None
            is_fk = col_name in foreign_keys
            if is_fk:
                ref_table, ref_col = foreign_keys[col_name]
            inline = re.search(
                r"\bREFERENCES\s+[`\"\[]?(\w+)[`\"\]]?\s*\(([^)]+)\)",
                line,
                re.IGNORECASE,
            )
            if inline:
                is_fk = True
                ref_table = inline.group(1)
                ref_col = _strip_quotes(inline.group(2).split(",")[0])

            table.columns.append(
                Column(
                    name=col_name,
                    data_type=data_type,
                    is_primary_key=is_pk,
                    is_foreign_key=is_fk,
                    is_not_null=is_not_null,
                    is_unique=is_unique,
                    references_table=ref_table,
                    references_column=ref_col,
                )
            )

        tables.append(table)

    return tables


def generate_mermaid_er(tables: List[Table]) -> str:
    """
    Produce a Mermaid erDiagram block from a list of parsed Table objects.

    Column markers:
        PK  — primary key
        FK  — foreign key
        UK  — unique key (non-PK)
    """
    lines = ["erDiagram"]

    relationships: List[Tuple[str, str, str]] = []

    for table in tables:
        lines.append(f"    {table.name} {{")
        for col in table.columns:
            if col.is_primary_key:
                marker = " PK"
            elif col.is_foreign_key:
                marker = " FK"
            elif col.is_unique:
                marker = " UK"
            else:
                marker = ""
            lines.append(f"        {col.data_type} {col.name}{marker}")
        lines.append("    }")

        for col in table.columns:
            if col.is_foreign_key and col.references_table:
                relationships.append((col.references_table, table.name, col.name))

    for ref_table, src_table, via_col in relationships:
        lines.append(f'    {ref_table} ||--o{{ {src_table} : "{via_col}"')

    return "\n".join(lines) + "\n"
