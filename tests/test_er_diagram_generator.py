import pytest
from db_tools.er_diagram_generator import (
    Column,
    Table,
    parse_sql_schema,
    generate_mermaid_er,
    _split_columns,
    _normalize_type,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

class TestHelpers:
    def test_normalize_type_strips_size(self):
        assert _normalize_type("VARCHAR(255)") == "VARCHAR"

    def test_normalize_type_uppercase(self):
        assert _normalize_type("datetime") == "DATETIME"

    def test_normalize_type_decimal(self):
        assert _normalize_type("DECIMAL(19,2)") == "DECIMAL"

    def test_split_columns_simple(self):
        parts = _split_columns("a INT, b VARCHAR(20), c BOOLEAN")
        assert len(parts) == 3

    def test_split_columns_nested_parens(self):
        # Comma inside DECIMAL(10,2) must not split
        parts = _split_columns("price DECIMAL(10,2), qty INT")
        assert len(parts) == 2


# ---------------------------------------------------------------------------
# parse_sql_schema – single table
# ---------------------------------------------------------------------------

SINGLE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS `users` (
    `id`    BIGINT      NOT NULL AUTO_INCREMENT,
    `email` VARCHAR(200) NOT NULL,
    `age`   INT,
    PRIMARY KEY (`id`),
    UNIQUE KEY uq_users_email (`email`)
) ENGINE=InnoDB;
"""


class TestParseSqlSchemaSingleTable:
    def setup_method(self):
        self.tables = parse_sql_schema(SINGLE_TABLE_SQL)

    def test_one_table(self):
        assert len(self.tables) == 1

    def test_table_name(self):
        assert self.tables[0].name == "users"

    def test_column_count(self):
        assert len(self.tables[0].columns) == 3

    def test_id_is_pk(self):
        id_col = next(c for c in self.tables[0].columns if c.name == "id")
        assert id_col.is_primary_key is True

    def test_email_is_unique(self):
        email_col = next(c for c in self.tables[0].columns if c.name == "email")
        assert email_col.is_unique is True

    def test_email_not_null(self):
        email_col = next(c for c in self.tables[0].columns if c.name == "email")
        assert email_col.is_not_null is True

    def test_age_nullable(self):
        age_col = next(c for c in self.tables[0].columns if c.name == "age")
        assert age_col.is_not_null is False

    def test_id_data_type(self):
        id_col = next(c for c in self.tables[0].columns if c.name == "id")
        assert id_col.data_type == "BIGINT"

    def test_email_data_type(self):
        email_col = next(c for c in self.tables[0].columns if c.name == "email")
        assert email_col.data_type == "VARCHAR"


# ---------------------------------------------------------------------------
# parse_sql_schema – multi-table with FK
# ---------------------------------------------------------------------------

MULTI_TABLE_SQL = """
CREATE TABLE users (
    id    BIGINT NOT NULL,
    email VARCHAR(100) NOT NULL,
    PRIMARY KEY (id)
);

CREATE TABLE orders (
    id      BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    total   DECIMAL(19,2) NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT fk_order_user FOREIGN KEY (user_id) REFERENCES users (id)
);
"""


class TestParseSqlSchemaMultiTable:
    def setup_method(self):
        self.tables = parse_sql_schema(MULTI_TABLE_SQL)
        self.by_name = {t.name: t for t in self.tables}

    def test_two_tables(self):
        assert len(self.tables) == 2

    def test_users_table_present(self):
        assert "users" in self.by_name

    def test_orders_table_present(self):
        assert "orders" in self.by_name

    def test_fk_detected(self):
        user_id_col = next(
            c for c in self.by_name["orders"].columns if c.name == "user_id"
        )
        assert user_id_col.is_foreign_key is True

    def test_fk_references_table(self):
        user_id_col = next(
            c for c in self.by_name["orders"].columns if c.name == "user_id"
        )
        assert user_id_col.references_table == "users"

    def test_non_fk_column(self):
        total_col = next(
            c for c in self.by_name["orders"].columns if c.name == "total"
        )
        assert total_col.is_foreign_key is False


# ---------------------------------------------------------------------------
# generate_mermaid_er
# ---------------------------------------------------------------------------

class TestGenerateMermaidEr:
    def _tables(self):
        users = Table(
            name="users",
            columns=[
                Column("id", "BIGINT", is_primary_key=True, is_not_null=True, is_unique=True),
                Column("email", "VARCHAR", is_not_null=True, is_unique=True),
                Column("age", "INT"),
            ],
        )
        orders = Table(
            name="orders",
            columns=[
                Column("id", "BIGINT", is_primary_key=True, is_not_null=True, is_unique=True),
                Column(
                    "user_id", "BIGINT",
                    is_foreign_key=True, is_not_null=True,
                    references_table="users", references_column="id",
                ),
                Column("total", "DECIMAL", is_not_null=True),
            ],
        )
        return [users, orders]

    def test_starts_with_erdiagram(self):
        out = generate_mermaid_er(self._tables())
        assert out.startswith("erDiagram")

    def test_users_block_present(self):
        out = generate_mermaid_er(self._tables())
        assert "users {" in out

    def test_orders_block_present(self):
        out = generate_mermaid_er(self._tables())
        assert "orders {" in out

    def test_pk_marker(self):
        out = generate_mermaid_er(self._tables())
        assert "BIGINT id PK" in out

    def test_fk_marker(self):
        out = generate_mermaid_er(self._tables())
        assert "BIGINT user_id FK" in out

    def test_relationship_line(self):
        out = generate_mermaid_er(self._tables())
        assert 'users ||--o{ orders : "user_id"' in out

    def test_no_relationship_for_non_fk(self):
        table = Table(
            name="simple",
            columns=[Column("id", "BIGINT", is_primary_key=True)],
        )
        out = generate_mermaid_er([table])
        assert "||--o{" not in out

    def test_empty_tables(self):
        out = generate_mermaid_er([])
        assert out.strip() == "erDiagram"
