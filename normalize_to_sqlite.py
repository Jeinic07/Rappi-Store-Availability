"""
normalize_to_sqlite.py
----------------------
Lee todos los CSVs de disponibilidad de Rappi y los carga en una base
de datos SQLite lista para ser consultada por el chatbot.

Uso:
    python normalize_to_sqlite.py                          # busca CSVs en la carpeta actual
    python normalize_to_sqlite.py --folder ./mis_csvs      # carpeta personalizada
    python normalize_to_sqlite.py --folder ./data --db availability.db

Requisitos: Python 3.8+ (solo librerías estándar, sin pip install)
"""

import csv
import sqlite3
import argparse
import glob
import os
import re
from datetime import datetime, timezone, timedelta


# ──────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────
DEFAULT_DB = "availability.db"
DEFAULT_FOLDER = "."

# Columnas fijas al inicio de cada CSV (antes de los timestamps)
FIXED_COLS = 4  # Plot name, metric, Value Prefix, Value Suffix


# ──────────────────────────────────────────────
# PARSEO DE TIMESTAMPS
# ──────────────────────────────────────────────
def parse_timestamp(raw: str) -> datetime | None:
    """
    Convierte el timestamp del header del CSV a un datetime en UTC.
    Formato de entrada: 'Sun Feb 01 2026 06:59:40 GMT-0500 (hora estándar de Colombia)'
    """
    raw = raw.strip()

    # Extraer la parte útil: 'Sun Feb 01 2026 06:59:40 GMT-0500'
    match = re.match(
        r"\w+\s+(\w+)\s+(\d+)\s+(\d{4})\s+(\d{2}:\d{2}:\d{2})\s+GMT([+-]\d{4})",
        raw
    )
    if not match:
        return None

    month_str, day, year, time_str, tz_offset = match.groups()

    # Construir string parseable
    dt_str = f"{day} {month_str} {year} {time_str} {tz_offset}"
    try:
        dt = datetime.strptime(dt_str, "%d %b %Y %H:%M:%S %z")
        return dt.astimezone(timezone.utc)  # normalizar a UTC
    except ValueError:
        return None


# ──────────────────────────────────────────────
# CREAR BASE DE DATOS
# ──────────────────────────────────────────────
def create_db(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS availability (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            recorded_at   TEXT NOT NULL,       -- ISO 8601 UTC: '2026-02-01T11:59:40+00:00'
            recorded_at_local TEXT NOT NULL,   -- hora Colombia: '2026-02-01 06:59:40'
            visible_stores INTEGER NOT NULL,
            source_file   TEXT NOT NULL        -- nombre del CSV de origen
        );

        -- Índices para acelerar las queries más comunes del chatbot
        CREATE INDEX IF NOT EXISTS idx_recorded_at       ON availability(recorded_at);
        CREATE INDEX IF NOT EXISTS idx_recorded_at_local ON availability(recorded_at_local);
        CREATE INDEX IF NOT EXISTS idx_source_file       ON availability(source_file);

        -- Vista útil para el chatbot: agrega por hora
        CREATE VIEW IF NOT EXISTS availability_by_hour AS
            SELECT
                substr(recorded_at_local, 1, 13) || ':00:00' AS hour,
                ROUND(AVG(visible_stores))                    AS avg_stores,
                MIN(visible_stores)                           AS min_stores,
                MAX(visible_stores)                           AS max_stores,
                COUNT(*)                                      AS data_points
            FROM availability
            GROUP BY substr(recorded_at_local, 1, 13);

        -- Vista por día
        CREATE VIEW IF NOT EXISTS availability_by_day AS
            SELECT
                substr(recorded_at_local, 1, 10) AS day,
                ROUND(AVG(visible_stores))        AS avg_stores,
                MIN(visible_stores)               AS min_stores,
                MAX(visible_stores)               AS max_stores,
                COUNT(*)                          AS data_points
            FROM availability
            GROUP BY substr(recorded_at_local, 1, 10);
    """)
    conn.commit()


# ──────────────────────────────────────────────
# CARGAR UN CSV
# ──────────────────────────────────────────────
COL_OFFSET = timedelta(hours=-5)  # GMT-0500 Colombia

def load_csv(conn: sqlite3.Connection, filepath: str) -> int:
    """
    Parsea un CSV y lo inserta en la DB.
    Retorna el número de filas insertadas.
    """
    filename = os.path.basename(filepath)
    rows_inserted = 0

    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)

        # Timestamps están en las columnas a partir de índice FIXED_COLS
        timestamps_raw = header[FIXED_COLS:]

        # Parsear todos los timestamps del header
        timestamps = [parse_timestamp(t) for t in timestamps_raw]

        for row in reader:
            if len(row) < FIXED_COLS + 1:
                continue  # fila vacía o malformada

            metric = row[1].strip()
            # Solo procesar la métrica de disponibilidad
            if "visible_stores" not in metric:
                continue

            values = row[FIXED_COLS:]

            records = []
            for i, val in enumerate(values):
                val = val.strip()
                if not val:
                    continue
                try:
                    stores = int(float(val))
                except ValueError:
                    continue

                ts_utc = timestamps[i] if i < len(timestamps) else None
                if ts_utc is None:
                    continue

                # Hora local Colombia (UTC-5)
                ts_local = ts_utc + COL_OFFSET
                recorded_at_local = ts_local.strftime("%Y-%m-%d %H:%M:%S")

                records.append((
                    ts_utc.isoformat(),
                    recorded_at_local,
                    stores,
                    filename
                ))

            if records:
                conn.executemany(
                    "INSERT INTO availability (recorded_at, recorded_at_local, visible_stores, source_file) VALUES (?, ?, ?, ?)",
                    records
                )
                rows_inserted += len(records)

    conn.commit()
    return rows_inserted


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Normaliza CSVs de Rappi a SQLite")
    parser.add_argument("--folder", default=DEFAULT_FOLDER, help="Carpeta con los CSVs (default: carpeta actual)")
    parser.add_argument("--db",     default=DEFAULT_DB,     help=f"Nombre del archivo SQLite (default: {DEFAULT_DB})")
    parser.add_argument("--reset",  action="store_true",    help="Borra la DB existente y empieza desde cero")
    args = parser.parse_args()

    # Buscar CSVs
    pattern = os.path.join(args.folder, "*.csv")
    csv_files = sorted(glob.glob(pattern))

    if not csv_files:
        print(f"❌ No se encontraron archivos .csv en: {args.folder}")
        return

    print(f"📂 Carpeta: {args.folder}")
    print(f"📄 CSVs encontrados: {len(csv_files)}")
    print(f"🗄️  Base de datos: {args.db}")
    print()

    # Resetear si se pide
    if args.reset and os.path.exists(args.db):
        os.remove(args.db)
        print("🗑️  DB anterior eliminada.\n")

    conn = sqlite3.connect(args.db)
    create_db(conn)

    # Verificar qué archivos ya están cargados (para no duplicar)
    already_loaded = set(
        row[0] for row in conn.execute("SELECT DISTINCT source_file FROM availability")
    )

    total_rows = 0
    skipped = 0
    errors = 0

    for i, filepath in enumerate(csv_files, 1):
        filename = os.path.basename(filepath)

        if filename in already_loaded:
            print(f"  [{i:03d}/{len(csv_files)}] ⏭️  Skipped (ya cargado): {filename}")
            skipped += 1
            continue

        try:
            n = load_csv(conn, filepath)
            total_rows += n
            print(f"  [{i:03d}/{len(csv_files)}] ✅ {filename} → {n:,} filas")
        except Exception as e:
            print(f"  [{i:03d}/{len(csv_files)}] ❌ Error en {filename}: {e}")
            errors += 1

    conn.close()

    print()
    print("─" * 50)
    print(f"✅ Filas insertadas:  {total_rows:,}")
    print(f"⏭️  CSVs ya cargados: {skipped}")
    print(f"❌ Errores:          {errors}")
    print(f"🗄️  Base de datos lista: {args.db}")
    print()
    print("Próximo paso: ejecuta verify_db.py para validar los datos.")


if __name__ == "__main__":
    main()
