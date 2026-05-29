import pytest
from db_tools.migration_generator import (
    ColumnDef,
    java_type_to_sql,
    parse_entity,
    generate_migration,
)


# ---------------------------------------------------------------------------
# java_type_to_sql
# ---------------------------------------------------------------------------

class TestJavaTypeToSql:
    def test_string_default_length(self):
        assert java_type_to_sql("String") == "VARCHAR(255)"

    def test_string_custom_length(self):
        assert java_type_to_sql("String", 100) == "VARCHAR(100)"

    def test_long(self):
        assert java_type_to_sql("Long") == "BIGINT"

    def test_primitive_long(self):
        assert java_type_to_sql("long") == "BIGINT"

    def test_integer(self):
        assert java_type_to_sql("Integer") == "INT"

    def test_boolean(self):
        assert java_type_to_sql("Boolean") == "BOOLEAN"

    def test_big_decimal(self):
        assert java_type_to_sql("BigDecimal") == "DECIMAL(19,2)"

    def test_local_date(self):
        assert java_type_to_sql("LocalDate") == "DATE"

    def test_local_date_time(self):
        assert java_type_to_sql("LocalDateTime") == "DATETIME"

    def test_uuid(self):
        assert java_type_to_sql("UUID") == "VARCHAR(36)"

    def test_unknown_object_type(self):
        # Unknown type starting with uppercase → VARCHAR(50) (enum-like)
        assert java_type_to_sql("MyEnum") == "VARCHAR(50)"

    def test_unknown_lowercase_type(self):
        assert java_type_to_sql("unknown") == "VARCHAR(255)"


# ---------------------------------------------------------------------------
# parse_entity
# ---------------------------------------------------------------------------

SIMPLE_ENTITY = """
package com.example;

import jakarta.persistence.*;

@Entity
@Table(name = "customers")
public class Customer {

    @Id
    @GeneratedValue
    private Long id;

    @Column(name = "email_address", nullable = false, unique = true, length = 150)
    private String email;

    @Column(name = "full_name", length = 80)
    private String name;

    @Column(nullable = false)
    private Integer age;
}
"""


class TestParseEntity:
    def setup_method(self):
        self.result = parse_entity(SIMPLE_ENTITY)

    def test_table_name(self):
        assert self.result["table_name"] == "customers"

    def test_id_field(self):
        col = self.result["columns"]["id"]
        assert col.is_id is True
        assert col.nullable is False

    def test_email_column_name(self):
        assert self.result["columns"]["email"].column_name == "email_address"

    def test_email_not_nullable(self):
        assert self.result["columns"]["email"].nullable is False

    def test_email_unique(self):
        assert self.result["columns"]["email"].unique is True

    def test_email_length(self):
        assert self.result["columns"]["email"].length == 150

    def test_name_column_name(self):
        assert self.result["columns"]["name"].column_name == "full_name"

    def test_name_nullable_default(self):
        assert self.result["columns"]["name"].nullable is True

    def test_age_not_nullable(self):
        assert self.result["columns"]["age"].nullable is False

    def test_camel_to_snake_fallback(self):
        # No @Table → class name used; no explicit @Column → camelCase→snake_case
        src = """
@Entity
public class OrderItem {
    @Id
    private Long id;
    @Column
    private String itemName;
}
"""
        r = parse_entity(src)
        assert r["table_name"] == "order_item"
        assert r["columns"]["itemName"].column_name == "item_name"


# ---------------------------------------------------------------------------
# generate_migration
# ---------------------------------------------------------------------------

V1 = """
@Entity
@Table(name = "products")
public class Product {
    @Id
    private Long id;

    @Column(name = "title", length = 200)
    private String name;

    @Column(name = "stock")
    private Integer qty;

    @Column(name = "old_col")
    private String legacy;
}
"""

V2 = """
@Entity
@Table(name = "products")
public class Product {
    @Id
    private Long id;

    @Column(name = "title", length = 200)
    private String name;

    @Column(name = "stock")
    private Integer qty;

    // old_col removed, price added, name made NOT NULL
    @Column(nullable = false)
    private java.math.BigDecimal price;

    @Column(name = "discount_pct")
    private Double discount;
}
"""


class TestGenerateMigration:
    def setup_method(self):
        self.sql = generate_migration(V1, V2, version="20250101000000")

    def test_header_present(self):
        assert "Flyway Migration Script" in self.sql

    def test_version_in_filename_hint(self):
        assert "V20250101000000" in self.sql

    def test_add_price_column(self):
        assert "ADD COLUMN price DECIMAL(19,2) NOT NULL" in self.sql

    def test_add_discount_column(self):
        assert "ADD COLUMN discount_pct DOUBLE" in self.sql

    def test_drop_old_col(self):
        assert "DROP COLUMN old_col" in self.sql

    def test_no_change_for_identical_entities(self):
        result = generate_migration(V1, V1)
        assert "No schema changes detected" in result

    def test_rename_column(self):
        old = """
@Entity
@Table(name = "t")
public class T {
    @Id private Long id;
    @Column(name = "old_name") private String field;
}
"""
        new = """
@Entity
@Table(name = "t")
public class T {
    @Id private Long id;
    @Column(name = "new_name") private String field;
}
"""
        sql = generate_migration(old, new)
        assert "RENAME COLUMN old_name TO new_name" in sql

    def test_type_change(self):
        old = """
@Entity
@Table(name = "t")
public class T {
    @Id private Long id;
    @Column private Integer score;
}
"""
        new = """
@Entity
@Table(name = "t")
public class T {
    @Id private Long id;
    @Column private Double score;
}
"""
        sql = generate_migration(old, new)
        assert "MODIFY COLUMN score DOUBLE" in sql
