"""
Flyway migration script generator.

Compares two JPA entity Java source files and produces ALTER TABLE DDL
statements compatible with Flyway versioned migrations.
"""
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional


@dataclass
class ColumnDef:
    name: str
    java_type: str
    column_name: str
    nullable: bool = True
    length: Optional[int] = None
    unique: bool = False
    is_id: bool = False


_JAVA_TO_SQL: Dict[str, str] = {
    "String": "VARCHAR",
    "Long": "BIGINT",
    "long": "BIGINT",
    "Integer": "INT",
    "int": "INT",
    "Short": "SMALLINT",
    "short": "SMALLINT",
    "Boolean": "BOOLEAN",
    "boolean": "BOOLEAN",
    "Double": "DOUBLE",
    "double": "DOUBLE",
    "Float": "FLOAT",
    "float": "FLOAT",
    "BigDecimal": "DECIMAL(19,2)",
    "Date": "DATE",
    "LocalDate": "DATE",
    "LocalDateTime": "DATETIME",
    "Instant": "TIMESTAMP",
    "ZonedDateTime": "TIMESTAMP",
    "UUID": "VARCHAR(36)",
    "byte[]": "BLOB",
    "Byte[]": "BLOB",
    "Text": "TEXT",
}


def _camel_to_snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def java_type_to_sql(java_type: str, length: Optional[int] = None) -> str:
    """Map a Java field type to a SQL column type string."""
    base = java_type.split("<")[0].strip()
    # Strip fully-qualified package prefix (e.g. java.math.BigDecimal → BigDecimal)
    if "." in base:
        base = base.split(".")[-1]
    sql = _JAVA_TO_SQL.get(base)
    if sql is None:
        # Enum or unknown object type → small VARCHAR
        return "VARCHAR(50)" if base[0].isupper() else "VARCHAR(255)"
    if sql == "VARCHAR":
        return f"VARCHAR({length or 255})"
    return sql


def parse_entity(java_source: str) -> dict:
    """
    Parse a JPA entity Java source file.

    Returns:
        {
          "table_name": str,
          "columns": {field_name: ColumnDef, ...}
        }
    """
    # Table name from @Table annotation or class name
    m = re.search(r'@Table\s*\([^)]*name\s*=\s*["\']([^"\']+)["\']', java_source)
    if m:
        table_name = m.group(1)
    else:
        cm = re.search(r'\bclass\s+(\w+)', java_source)
        table_name = _camel_to_snake(cm.group(1)) if cm else "unknown_table"

    columns: Dict[str, ColumnDef] = {}

    # Normalize same-line annotations: "@Column(...) private T f;" → two lines.
    # This lets the field_re below work uniformly with multi-line annotation style.
    java_source = re.sub(
        r'(@\w+(?:\([^)]*\))?)\s+(private|protected|public)\s+',
        r'\1\n\2 ',
        java_source,
    )

    # Match annotation blocks + field declarations (multi-line annotation style).
    field_re = re.compile(
        r'((?:[ \t]*@[^\n]+\n)*)'      # group 1: zero-or-more annotation lines
        r'[ \t]*(private|protected|public)\s+'  # group 2: access modifier
        r'([\w.<>?,]+)\s+'             # group 3: type (supports FQCNs with dots)
        r'(\w+)\s*;',                   # group 4: field name
        re.MULTILINE,
    )

    for match in field_re.finditer(java_source):
        annotations = match.group(1)
        java_type = match.group(3).strip()
        field_name = match.group(4)

        # Skip relationship / transient fields
        skip_markers = ("@Transient", "@OneToMany", "@ManyToMany", "@ManyToOne", "@OneToOne")
        if any(m in annotations for m in skip_markers):
            continue

        # --- column name ---
        col_match = re.search(r'@Column\s*\([^)]*\bname\s*=\s*["\']([^"\']+)["\']', annotations)
        column_name = col_match.group(1) if col_match else _camel_to_snake(field_name)

        # --- nullable ---
        is_id = "@Id" in annotations
        nullable = True
        if is_id:
            nullable = False
        else:
            nn_match = re.search(r'\bnullable\s*=\s*(true|false)', annotations)
            if nn_match:
                nullable = nn_match.group(1) == "true"
            if re.search(r'@(?:NotNull|NonNull)\b', annotations):
                nullable = False

        # --- length ---
        length: Optional[int] = None
        len_match = re.search(r'\blength\s*=\s*(\d+)', annotations)
        if len_match:
            length = int(len_match.group(1))
        size_match = re.search(r'@Size\s*\([^)]*\bmax\s*=\s*(\d+)', annotations)
        if size_match:
            length = int(size_match.group(1))

        # --- unique ---
        unique = bool(re.search(r'\bunique\s*=\s*true', annotations))

        columns[field_name] = ColumnDef(
            name=field_name,
            java_type=java_type,
            column_name=column_name,
            nullable=nullable,
            length=length,
            unique=unique,
            is_id=is_id,
        )

    return {"table_name": table_name, "columns": columns}


def generate_migration(
    old_source: str,
    new_source: str,
    version: Optional[str] = None,
) -> str:
    """
    Generate a Flyway-compatible migration script by diffing two entity versions.

    Args:
        old_source: Java source of the previous entity version.
        new_source: Java source of the current entity version.
        version:    Optional version string (e.g. "20250510120000").
                    Defaults to current timestamp.

    Returns:
        SQL migration script as a string.
    """
    old = parse_entity(old_source)
    new = parse_entity(new_source)
    table = new["table_name"] or old["table_name"]
    old_cols: Dict[str, ColumnDef] = old["columns"]
    new_cols: Dict[str, ColumnDef] = new["columns"]

    statements = []

    # 1. Added columns
    for field, col in new_cols.items():
        if field not in old_cols:
            sql_type = java_type_to_sql(col.java_type, col.length)
            not_null = " NOT NULL" if not col.nullable else ""
            unique = " UNIQUE" if col.unique else ""
            statements.append(
                f"ALTER TABLE {table} ADD COLUMN {col.column_name} {sql_type}{not_null}{unique};"
            )

    # 2. Dropped columns
    for field, col in old_cols.items():
        if field not in new_cols:
            statements.append(f"ALTER TABLE {table} DROP COLUMN {col.column_name};")

    # 3. Modified columns
    for field, new_col in new_cols.items():
        if field not in old_cols:
            continue
        old_col = old_cols[field]

        # Rename
        if old_col.column_name != new_col.column_name:
            statements.append(
                f"ALTER TABLE {table} RENAME COLUMN {old_col.column_name} TO {new_col.column_name};"
            )
            # After rename, check type/nullability against new name
            old_type = java_type_to_sql(old_col.java_type, old_col.length)
            new_type = java_type_to_sql(new_col.java_type, new_col.length)
            if old_type != new_type or old_col.nullable != new_col.nullable:
                not_null = " NOT NULL" if not new_col.nullable else ""
                statements.append(
                    f"ALTER TABLE {table} MODIFY COLUMN {new_col.column_name} {new_type}{not_null};"
                )
        else:
            old_type = java_type_to_sql(old_col.java_type, old_col.length)
            new_type = java_type_to_sql(new_col.java_type, new_col.length)
            if old_type != new_type or old_col.nullable != new_col.nullable:
                not_null = " NOT NULL" if not new_col.nullable else ""
                statements.append(
                    f"ALTER TABLE {table} MODIFY COLUMN {new_col.column_name} {new_type}{not_null};"
                )

        # Unique constraint changes
        if not old_col.unique and new_col.unique:
            statements.append(
                f"ALTER TABLE {table} ADD UNIQUE INDEX uq_{table}_{new_col.column_name} ({new_col.column_name});"
            )
        elif old_col.unique and not new_col.unique:
            statements.append(
                f"ALTER TABLE {table} DROP INDEX uq_{table}_{old_col.column_name};"
            )

    if not statements:
        return f"-- No schema changes detected for table {table}\n"

    ver = version or datetime.now().strftime("%Y%m%d%H%M%S")
    header = (
        f"-- Flyway Migration Script\n"
        f"-- Suggested filename: V{ver}__alter_{table}.sql\n"
        f"-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"-- Table: {table}\n\n"
    )
    return header + "\n".join(statements) + "\n"
