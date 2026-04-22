"""
config.py — Configuración centralizada de la aplicación.
Todas las constantes y parámetros de entorno se leen aquí
para evitar magic strings dispersos en el código.
"""

import os

# ── Base de datos ──────────────────────────────────────────
DB_PATH: str = os.environ.get("DB_PATH", "availability.db")

# ── API de Anthropic ───────────────────────────────────────
ANTHROPIC_API_URL: str = "https://api.anthropic.com/v1/messages"
ANTHROPIC_API_VERSION: str = "2023-06-01"
CLAUDE_MODEL: str = "claude-opus-4-5"
CLAUDE_MAX_TOKENS: int = 400

# ── Servidor ───────────────────────────────────────────────
SERVER_PORT: int = int(os.environ.get("PORT", 5000))
DEBUG: bool = os.environ.get("FLASK_DEBUG", "true").lower() == "true"
