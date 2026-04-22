"""
database/connection.py — Capa de infraestructura: gestión de conexiones SQLite.

Responsabilidad única: abrir, configurar y cerrar conexiones a la base de datos.
Ninguna otra capa debería importar `sqlite3` directamente.
"""

import sqlite3
from typing import List, Any
from config import DB_PATH


def get_conn() -> sqlite3.Connection:
    """
    Abre una conexión SQLite configurada con row_factory para
    que cada fila se pueda tratar como un diccionario.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def rows_to_list(rows: List[sqlite3.Row]) -> List[dict]:
    """Convierte una lista de sqlite3.Row a una lista de diccionarios serializables."""
    return [dict(row) for row in rows]
