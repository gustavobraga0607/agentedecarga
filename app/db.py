"""Acesso a banco: SQLite (local) ou Postgres (quando há DATABASE_URL).

As consultas são escritas com placeholders `?`; a conexão Postgres os
converte para `%s`. Inserções que precisam do id usam `inserir()`.
"""

import sqlite3
from datetime import date
from pathlib import Path

from flask import current_app, g

try:
    import psycopg
    from psycopg.rows import dict_row

    IntegrityError = (sqlite3.IntegrityError, psycopg.IntegrityError)
except ImportError:  # psycopg só é necessário com Postgres
    psycopg = None
    IntegrityError = (sqlite3.IntegrityError,)


class Conexao:
    def __init__(self, url_postgres=None, caminho_sqlite=None):
        self.pg = bool(url_postgres)
        if self.pg:
            if psycopg is None:
                raise RuntimeError("Instale psycopg para usar Postgres.")
            self.raw = psycopg.connect(url_postgres, row_factory=dict_row)
        else:
            self.raw = sqlite3.connect(caminho_sqlite)
            self.raw.row_factory = sqlite3.Row
            self.raw.execute("PRAGMA foreign_keys = ON")

    def execute(self, sql, args=()):
        if self.pg:
            cur = self.raw.cursor()
            cur.execute(sql.replace("?", "%s"), tuple(args))
            return cur
        return self.raw.execute(sql, tuple(args))

    def inserir(self, sql, args=()):
        """Executa um INSERT e retorna o id gerado."""
        if self.pg:
            return self.execute(sql + " RETURNING id", args).fetchone()["id"]
        return self.execute(sql, args).lastrowid

    def executescript(self, script):
        if self.pg:
            self.raw.execute(script)
        else:
            self.raw.executescript(script)

    def commit(self):
        self.raw.commit()

    def rollback(self):
        self.raw.rollback()

    def close(self):
        self.raw.close()


def get_db():
    if "db" not in g:
        g.db = Conexao(current_app.config.get("DATABASE_URL"), current_app.config["DATABASE"])
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    arquivo = "schema_pg.sql" if db.pg else "schema.sql"
    db.executescript((Path(__file__).parent / arquivo).read_text(encoding="utf-8"))
    db.commit()


def query(sql, args=(), one=False):
    rows = get_db().execute(sql, args).fetchall()
    return (rows[0] if rows else None) if one else rows


def execute(sql, args=()):
    db = get_db()
    try:
        if sql.lstrip().upper().startswith("INSERT"):
            novo_id = db.inserir(sql, args)
        else:
            db.execute(sql, args)
            novo_id = None
        db.commit()
    except Exception:
        db.rollback()
        raise
    return novo_id


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
