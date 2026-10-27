"""Conexão com o MySQL.

As configurações vêm de variáveis de ambiente; os valores padrão funcionam
com o MySQL do XAMPP (usuário root, sem senha):
    DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
"""
import os
from contextlib import contextmanager

import pymysql
from flask import g

CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": int(os.environ.get("DB_PORT", "3306")),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", ""),
    "database": os.environ.get("DB_NAME", "deskly"),
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,  # cada linha vem como dicionário
    "autocommit": True,
}

# Erro de chave duplicada / chave estrangeira, para as rotas tratarem.
ErroIntegridade = pymysql.err.IntegrityError


def conexao():
    """Uma conexão por requisição, guardada no `g` do Flask."""
    if "db" not in g:
        g.db = pymysql.connect(**CONFIG)
    return g.db


def fechar_conexao(_erro=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def consultar(sql, params=()):
    """SELECT que devolve uma lista de dicionários."""
    with conexao().cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def consultar_um(sql, params=()):
    """SELECT que devolve um dicionário (ou None se não achar nada)."""
    with conexao().cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def executar(sql, params=()):
    """INSERT/UPDATE/DELETE. Devolve o id gerado (INSERT) ou o nº de linhas afetadas."""
    with conexao().cursor() as cur:
        cur.execute(sql, params)
        return cur.lastrowid or cur.rowcount


@contextmanager
def transacao():
    """Agrupa vários comandos: ou todos são gravados, ou nenhum."""
    db = conexao()
    db.begin()
    try:
        yield
        db.commit()
    except Exception:
        db.rollback()
        raise
