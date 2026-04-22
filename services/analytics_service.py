"""
services/analytics_service.py — Servicio de analítica de disponibilidad.

Responsabilidad única: orquestar las llamadas al repositorio y exponer
operaciones de negocio a las rutas HTTP.

Principio de inversión de dependencias: depende de AvailabilityRepository
(abstracción de datos), no de sqlite3 directamente.
"""

from typing import List, Optional
from database.connection import get_conn
from repositories.availability_repository import AvailabilityRepository


class AnalyticsService:
    """
    Orquesta las operaciones de analítica de disponibilidad.
    Gestiona el ciclo de vida de la conexión y delega las
    queries al repositorio.
    """

    def _repo(self) -> tuple:
        """
        Abre una conexión y devuelve (conexión, repositorio).
        El llamador es responsable de cerrar la conexión.
        """
        conn = get_conn()
        return conn, AvailabilityRepository(conn)

    # ── Métodos de negocio ─────────────────────────────────────────────────────

    def get_summary(self) -> dict:
        """KPIs globales para las tarjetas del dashboard."""
        conn, repo = self._repo()
        try:
            return repo.get_summary()
        finally:
            conn.close()

    def get_timeseries(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> List[dict]:
        """Serie de tiempo agrupada por minuto, con filtro opcional de fechas."""
        conn, repo = self._repo()
        try:
            return repo.get_timeseries(date_from, date_to)
        finally:
            conn.close()

    def get_by_hour(self) -> List[dict]:
        """Distribución promedio de tiendas por hora del día."""
        conn, repo = self._repo()
        try:
            return repo.get_by_hour()
        finally:
            conn.close()

    def get_by_day(self) -> List[dict]:
        """Tendencia diaria de disponibilidad."""
        conn, repo = self._repo()
        try:
            return repo.get_by_day()
        finally:
            conn.close()

    def get_anomalies(self) -> List[dict]:
        """Registros con caídas anómalas de disponibilidad."""
        conn, repo = self._repo()
        try:
            return repo.get_anomalies()
        finally:
            conn.close()

    def get_heatmap(self) -> List[dict]:
        """Datos para el heatmap día de semana × hora."""
        conn, repo = self._repo()
        try:
            return repo.get_heatmap()
        finally:
            conn.close()

    def get_health_score(self) -> dict:
        """
        Índice de Salud Operacional (0–100) compuesto por:
          · Estabilidad   40 % → baja variación relativa = bueno
          · Confiabilidad 35 % → pocos eventos anómalos = bueno
          · Cobertura     25 % → promedio cercano al máximo = bueno
        """
        import math

        conn, repo = self._repo()
        try:
            raw = repo.get_health_score()
        finally:
            conn.close()

        avg   = raw["avg_stores"]  or 0.0
        avg_sq = raw["avg_sq"]     or 0.0
        maxi  = raw["max_stores"]  or 1.0
        total = raw["total_records"] or 1
        anomalies = raw["anomaly_count"] or 0

        # Desviación estándar por identidad E[X²] - E[X]²
        variance = max(0.0, avg_sq - avg ** 2)
        std = math.sqrt(variance)

        # Coeficiente de variación (0 = perfecto, >1 = muy inestable)
        cv = (std / avg) if avg else 1.0
        stability    = max(0, min(100, round((1 - cv) * 100)))

        # Tasa de anomalías respecto al total de registros
        anomaly_rate = anomalies / total
        reliability  = max(0, min(100, round((1 - anomaly_rate) * 100)))

        # Cobertura: qué tan cerca opera del pico histórico
        coverage = max(0, min(100, round((avg / maxi) * 100))) if maxi else 0

        score = round(stability * 0.40 + reliability * 0.35 + coverage * 0.25)

        return {
            "score":         score,
            "stability":     stability,
            "reliability":   reliability,
            "coverage":      coverage,
            "avg_stores":    round(avg),
            "total_records": total,
            "anomaly_count": anomalies,
        }
