"""Cau hinh test dung chung: cho phep tao schema MySQL tren SQLite in-memory."""
from sqlalchemy.dialects.mysql import BIGINT, ENUM
from sqlalchemy.ext.compiler import compiles


@compiles(BIGINT, "sqlite")
def _bigint_sqlite(t, c, **k):
    return "INTEGER"


@compiles(ENUM, "sqlite")
def _enum_sqlite(t, c, **k):
    return "VARCHAR(32)"


import app.main  # noqa: E402,F401  (import day du model de mapper cau hinh du)
