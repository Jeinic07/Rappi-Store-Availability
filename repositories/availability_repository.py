"""
repositories/availability_repository.py — Repositorio de datos de disponibilidad.

Responsabilidad única: encapsular todas las queries SQL contra la tabla `availability`.
No contiene lógica de negocio ni conoce nada del protocolo HTTP.

Principio de inversión de dependencias: recibe la conexión desde fuera,
lo que permite sustituir la fuente de datos sin modificar las capas superiores.
"""

import sqlite3
from typing import List, Optional
from database.connection import rows_to_list


class AvailabilityRepository:
    """
    Accede a la tabla `availability` de la base de datos.
    Cada método corresponde a una consulta de dominio específica.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    # ── KPIs globales ──────────────────────────────────────────────────────────
    def get_summary(self) -> dict:
        """Estadísticas globales: rango de fechas, promedio, mín y máx de tiendas."""
        row = self._conn.execute("""
            SELECT
                COUNT(*)                                    AS total_records,
                COUNT(DISTINCT source_file)                 AS total_files,
                MIN(recorded_at_local)                      AS date_from,
                MAX(recorded_at_local)                      AS date_to,
                ROUND(AVG(visible_stores))                  AS avg_stores,
                MIN(visible_stores)                         AS min_stores,
                MAX(visible_stores)                         AS max_stores
            FROM availability
        """).fetchone()
        return dict(row)

    # ── Serie de tiempo ────────────────────────────────────────────────────────
    def get_timeseries(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> List[dict]:
        """
        Agrupación por minuto para el gráfico principal.
        Filtra opcionalmente por rango de fechas.
        """
        where = ""
        params: List[str] = []

        if date_from:
            where += " AND recorded_at_local >= ?"
            params.append(date_from)
        if date_to:
            where += " AND recorded_at_local <= ?"
            params.append(date_to)

        rows = self._conn.execute(f"""
            SELECT
                substr(recorded_at_local, 1, 16) || ':00' AS minute,
                ROUND(AVG(visible_stores))                 AS avg_stores,
                MIN(visible_stores)                        AS min_stores,
                MAX(visible_stores)                        AS max_stores
            FROM availability
            WHERE 1=1 {where}
            GROUP BY substr(recorded_at_local, 1, 16)
            ORDER BY minute
            LIMIT 15000
        """, params).fetchall()
        return rows_to_list(rows)

    # ── Distribución por hora ──────────────────────────────────────────────────
    def get_by_hour(self) -> List[dict]:
        """Promedio de tiendas visibles por hora del día (0–23)."""
        rows = self._conn.execute("""
            SELECT
                CAST(substr(recorded_at_local, 12, 2) AS INTEGER) AS hour_of_day,
                ROUND(AVG(visible_stores))                        AS avg_stores,
                MIN(visible_stores)                               AS min_stores,
                MAX(visible_stores)                               AS max_stores
            FROM availability
            GROUP BY hour_of_day
            ORDER BY hour_of_day
        """).fetchall()
        return rows_to_list(rows)

    # ── Tendencia diaria ───────────────────────────────────────────────────────
    def get_by_day(self) -> List[dict]:
        """Promedio, mínimo y máximo de tiendas por día calendario."""
        rows = self._conn.execute("""
            SELECT
                substr(recorded_at_local, 1, 10) AS day,
                ROUND(AVG(visible_stores))        AS avg_stores,
                MIN(visible_stores)               AS min_stores,
                MAX(visible_stores)               AS max_stores,
                COUNT(*)                          AS data_points
            FROM availability
            GROUP BY day
            ORDER BY day
        """).fetchall()
        return rows_to_list(rows)

    # ── Anomalías ──────────────────────────────────────────────────────────────
    def get_anomalies(self) -> List[dict]:
        """
        Registros donde la disponibilidad cayó más del 15 %
        respecto al promedio de su hora, en horas con más de 1 000 tiendas promedio.
        """
        rows = self._conn.execute("""
            WITH hour_avg AS (
                SELECT
                    substr(recorded_at_local, 1, 13) AS hour_key,
                    AVG(visible_stores)               AS avg_hour
                FROM availability
                GROUP BY hour_key
            )
            SELECT
                a.recorded_at_local,
                a.visible_stores,
                ROUND(h.avg_hour)                                          AS avg_hour,
                ROUND((a.visible_stores - h.avg_hour) / h.avg_hour * 100, 1) AS pct_diff
            FROM availability a
            JOIN hour_avg h ON substr(a.recorded_at_local, 1, 13) = h.hour_key
            WHERE a.visible_stores < h.avg_hour * 0.85
              AND h.avg_hour > 1000
            ORDER BY pct_diff ASC
            LIMIT 200
        """).fetchall()
        return rows_to_list(rows)

    # ── Heatmap ────────────────────────────────────────────────────────────────
    def get_heatmap(self) -> List[dict]:
        """Datos para el heatmap: promedio de tiendas por día de semana × hora."""
        rows = self._conn.execute("""
            SELECT
                CAST(strftime('%w', recorded_at_local) AS INTEGER) AS weekday,
                CAST(substr(recorded_at_local, 12, 2) AS INTEGER)  AS hour_of_day,
                ROUND(AVG(visible_stores))                         AS avg_stores
            FROM availability
            GROUP BY weekday, hour_of_day
            ORDER BY weekday, hour_of_day
        """).fetchall()
        return rows_to_list(rows)

    # ── Datos de contexto para el chatbot ──────────────────────────────────────
    def get_context_data(self) -> dict:
        """
        Consolida en una sola conexión todos los datos que el chatbot
        necesita para construir su prompt de sistema.
        """
        summary = self.get_summary()

        by_day = rows_to_list(self._conn.execute("""
            SELECT substr(recorded_at_local,1,10) AS day,
                   ROUND(AVG(visible_stores))     AS avg,
                   MIN(visible_stores)            AS min,
                   MAX(visible_stores)            AS max
            FROM availability
            GROUP BY day
            ORDER BY day
        """).fetchall())

        by_hour = rows_to_list(self._conn.execute("""
            SELECT CAST(substr(recorded_at_local,12,2) AS INTEGER) AS hour,
                   ROUND(AVG(visible_stores))                      AS avg
            FROM availability
            GROUP BY hour
            ORDER BY hour
        """).fetchall())

        top_anomalies = rows_to_list(self._conn.execute("""
            WITH ha AS (
                SELECT substr(recorded_at_local,1,13) AS hk,
                       AVG(visible_stores)             AS ah
                FROM availability
                GROUP BY hk
            )
            SELECT a.recorded_at_local,
                   a.visible_stores,
                   ROUND((a.visible_stores - ha.ah) / ha.ah * 100, 1) AS pct_diff
            FROM availability a
            JOIN ha ON substr(a.recorded_at_local,1,13) = ha.hk
            WHERE a.visible_stores < ha.ah * 0.85
              AND ha.ah > 1000
            ORDER BY pct_diff ASC
            LIMIT 5
        """).fetchall())

        return {
            "summary": summary,
            "by_day": by_day,
            "by_hour": by_hour,
            "top_anomalies": top_anomalies,
        }

    # ── Índice de Salud Operacional ────────────────────────────────────────────
    def get_health_score(self) -> dict:
        """
        Devuelve las métricas brutas necesarias para calcular el
        Índice de Salud Operacional en la capa de servicio.
        Usa AVG(x²) para derivar la varianza sin SQRT en SQLite.
        """
        row = self._conn.execute("""
            WITH base_stats AS (
                SELECT
                    AVG(visible_stores)                        AS avg_val,
                    AVG(visible_stores * visible_stores)       AS avg_sq,
                    MAX(visible_stores)                        AS max_val,
                    COUNT(*)                                   AS total
                FROM availability
            ),
            anom_count AS (
                SELECT COUNT(*) AS anomalies
                FROM availability a, base_stats b
                WHERE a.visible_stores < b.avg_val * 0.85
                  AND b.avg_val > 1000
            )
            SELECT
                ROUND(b.avg_val)   AS avg_stores,
                b.avg_sq           AS avg_sq,
                ROUND(b.max_val)   AS max_stores,
                b.total            AS total_records,
                a.anomalies        AS anomaly_count
            FROM base_stats b, anom_count a
        """).fetchone()
        return dict(row)
