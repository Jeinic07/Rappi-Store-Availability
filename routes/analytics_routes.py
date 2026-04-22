"""
routes/analytics_routes.py — Blueprint Flask para los endpoints de analítica.

Responsabilidad única: traducir requests HTTP a llamadas al servicio
y serializar los resultados como JSON.
No contiene lógica de negocio ni queries SQL.

Principio de segregación de interfaces: solo expone las rutas de datos;
el chatbot tiene su propio blueprint.
"""

from flask import Blueprint, jsonify, request
from services.analytics_service import AnalyticsService

analytics_bp = Blueprint("analytics", __name__)
_service = AnalyticsService()


@analytics_bp.route("/api/summary")
def summary():
    """KPIs globales para las tarjetas del dashboard."""
    return jsonify(_service.get_summary())


@analytics_bp.route("/api/timeseries")
def timeseries():
    """
    Serie de tiempo agrupada por minuto.
    Query params opcionales: date_from, date_to (YYYY-MM-DD HH:MM:SS)
    """
    date_from = request.args.get("date_from") or None
    date_to   = request.args.get("date_to")   or None
    return jsonify(_service.get_timeseries(date_from, date_to))


@analytics_bp.route("/api/by_hour")
def by_hour():
    """Promedio de tiendas visibles por hora del día (0–23)."""
    return jsonify(_service.get_by_hour())


@analytics_bp.route("/api/by_day")
def by_day():
    """Promedio diario para el gráfico de tendencia."""
    return jsonify(_service.get_by_day())


@analytics_bp.route("/api/anomalies")
def anomalies():
    """Registros donde la disponibilidad cayó >15 % respecto al promedio de su hora."""
    return jsonify(_service.get_anomalies())


@analytics_bp.route("/api/heatmap")
def heatmap():
    """Datos para el heatmap: día de semana × hora del día."""
    return jsonify(_service.get_heatmap())


@analytics_bp.route("/api/health_score")
def health_score():
    """Índice de Salud Operacional compuesto (0–100) con sus componentes."""
    return jsonify(_service.get_health_score())
