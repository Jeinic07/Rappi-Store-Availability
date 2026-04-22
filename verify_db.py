"""
verify_db.py
------------
Verifica que la base de datos SQLite esté bien cargada y muestra
un resumen de los datos disponibles.

Uso:
    python verify_db.py
    python verify_db.py --db availability.db
"""

import sqlite3
import argparse

DEFAULT_DB = "availability.db"


def verify(db_path: str):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    print("=" * 55)
    print("  VERIFICACIÓN DE BASE DE DATOS")
    print("=" * 55)

    # ── Totales ──────────────────────────────────────────
    total = conn.execute("SELECT COUNT(*) FROM availability").fetchone()[0]
    files = conn.execute("SELECT COUNT(DISTINCT source_file) FROM availability").fetchone()[0]
    print(f"\n📊 Total de registros:  {total:,}")
    print(f"📄 Archivos CSV cargados: {files}")

    # ── Rango de fechas ──────────────────────────────────
    rng = conn.execute("""
        SELECT MIN(recorded_at_local), MAX(recorded_at_local) FROM availability
    """).fetchone()
    print(f"\n📅 Período cubierto:")
    print(f"   Desde: {rng[0]}")
    print(f"   Hasta: {rng[1]}")

    # ── Disponibilidad global ─────────────────────────────
    stats = conn.execute("""
        SELECT
            ROUND(AVG(visible_stores)) as avg,
            MIN(visible_stores)        as min,
            MAX(visible_stores)        as max
        FROM availability
    """).fetchone()
    print(f"\n🏪 Tiendas visibles (global):")
    print(f"   Promedio: {stats['avg']:,.0f}")
    print(f"   Mínimo:   {stats['min']:,}")
    print(f"   Máximo:   {stats['max']:,}")

    # ── Top 5 horas con más tiendas ───────────────────────
    print(f"\n🔝 Top 5 horas con MÁS tiendas (promedio):")
    rows = conn.execute("""
        SELECT hour, avg_stores, data_points
        FROM availability_by_hour
        ORDER BY avg_stores DESC
        LIMIT 5
    """).fetchall()
    for r in rows:
        print(f"   {r['hour']}  →  {r['avg_stores']:>8,.0f} tiendas  ({r['data_points']} muestras)")

    # ── Top 5 horas con menos tiendas ────────────────────
    print(f"\n📉 Top 5 horas con MENOS tiendas (promedio):")
    rows = conn.execute("""
        SELECT hour, avg_stores, data_points
        FROM availability_by_hour
        ORDER BY avg_stores ASC
        LIMIT 5
    """).fetchall()
    for r in rows:
        print(f"   {r['hour']}  →  {r['avg_stores']:>8,.0f} tiendas  ({r['data_points']} muestras)")

    # ── Disponibilidad por día ────────────────────────────
    print(f"\n📆 Disponibilidad por día:")
    rows = conn.execute("""
        SELECT day, avg_stores, min_stores, max_stores
        FROM availability_by_day
        ORDER BY day
    """).fetchall()
    for r in rows:
        print(f"   {r['day']}  avg={r['avg_stores']:>8,.0f}  min={r['min_stores']:,}  max={r['max_stores']:,}")

    # ── Posibles anomalías (caídas bruscas) ───────────────
    print(f"\n⚠️  Posibles anomalías (registros donde las tiendas cayeron >10% respecto al promedio del día):")
    anomalies = conn.execute("""
        WITH day_avg AS (
            SELECT substr(recorded_at_local, 1, 10) as day,
                   AVG(visible_stores) as avg_day
            FROM availability
            GROUP BY day
        )
        SELECT a.recorded_at_local, a.visible_stores, d.avg_day,
               ROUND((a.visible_stores - d.avg_day) / d.avg_day * 100, 1) as pct_diff
        FROM availability a
        JOIN day_avg d ON substr(a.recorded_at_local, 1, 10) = d.day
        WHERE a.visible_stores < d.avg_day * 0.90
        ORDER BY pct_diff ASC
        LIMIT 10
    """).fetchall()
    if anomalies:
        for r in anomalies:
            print(f"   {r['recorded_at_local']}  {r['visible_stores']:,} tiendas  ({r['pct_diff']:+.1f}% vs promedio del día {r['avg_day']:,.0f})")
    else:
        print("   ✅ No se detectaron anomalías significativas.")

    print()
    print("=" * 55)
    print("  Base de datos verificada correctamente ✅")
    print("=" * 55)

    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=DEFAULT_DB)
    args = parser.parse_args()
    verify(args.db)
