import sqlite3
from datetime import date
from pathlib import Path

from flask import current_app, g


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    schema = (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")
    get_db().executescript(schema)
    get_db().commit()


def query(sql, args=(), one=False):
    cur = get_db().execute(sql, args)
    rows = cur.fetchall()
    return (rows[0] if rows else None) if one else rows


def execute(sql, args=()):
    db = get_db()
    cur = db.execute(sql, args)
    db.commit()
    return cur.lastrowid


def empresa():
    return query("SELECT * FROM empresa WHERE id = 1", one=True)


def proximo_codigo(tabela, coluna, prefixo):
    """Gera códigos sequenciais por ano, ex.: ORC-2026-0001."""
    ano = date.today().year
    base = f"{prefixo}-{ano}-"
    row = query(
        f"SELECT {coluna} AS c FROM {tabela} WHERE {coluna} LIKE ? ORDER BY {coluna} DESC LIMIT 1",
        (base + "%",),
        one=True,
    )
    seq = int(row["c"].rsplit("-", 1)[1]) + 1 if row else 1
    return f"{base}{seq:04d}"
