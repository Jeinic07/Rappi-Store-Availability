"""
services/chat_service.py — Servicio de integración con la API de Claude (Anthropic).

Responsabilidades:
  1. Construir el prompt de sistema con contexto estadístico de la DB.
  2. Enviar mensajes a la API de Anthropic y devolver la respuesta.

Principio de inversión de dependencias: no importa `flask.request` ni `sqlite3`
directamente; recibe los datos que necesita a través de parámetros.
"""

import json
import requests
from typing import List

from config import (
    ANTHROPIC_API_URL,
    ANTHROPIC_API_VERSION,
    CLAUDE_MODEL,
    CLAUDE_MAX_TOKENS,
)
from database.connection import get_conn
from repositories.availability_repository import AvailabilityRepository


class ChatService:
    """
    Encapsula la comunicación con la API de Anthropic Claude.
    Construye el prompt de sistema con datos reales de la base de datos
    e interpreta la respuesta del modelo.
    """

    # ── Construcción del contexto ──────────────────────────────────────────────

    def build_system_prompt(self) -> str:
        """
        Genera el prompt de sistema con un resumen estadístico
        extraído de la base de datos.
        """
        conn = get_conn()
        try:
            repo = AvailabilityRepository(conn)
            data = repo.get_context_data()
        finally:
            conn.close()

        summary = data["summary"]

        return f"""
Eres un analista de datos de Rappi especializado en disponibilidad de tiendas.
Tienes acceso a datos históricos de disponibilidad de tiendas en la plataforma Rappi.

RESUMEN DE LOS DATOS:
- Período: {summary['date_from']} a {summary['date_to']}
- Total de registros: {summary['total_records']:,}
- Tiendas visibles: promedio={summary['avg_stores']:,}  mín={summary['min_stores']:,}  máx={summary['max_stores']:,}

DISPONIBILIDAD PROMEDIO POR DÍA:
{json.dumps(data['by_day'], indent=2)}

DISPONIBILIDAD PROMEDIO POR HORA DEL DÍA (hora Colombia):
{json.dumps(data['by_hour'], indent=2)}

TOP 5 ANOMALÍAS DETECTADAS (caídas más bruscas):
{json.dumps(data['top_anomalies'], indent=2)}

Responde en español, de forma concisa y orientada al negocio.
Si te preguntan algo que no está en los datos, dilo claramente.
Cuando des números de tiendas, formatea con separadores de miles.

FORMATO DE RESPUESTA (MUY IMPORTANTE):
- Escribe SOLO texto plano. Nunca uses Markdown.
- Prohibido usar: **, *, ##, ###, -, >, `, _, ~, o cualquier otro símbolo de formato.
- No uses listas con guiones ni asteriscos. Si necesitas listar elementos, usa números (1. 2. 3.).
- REGLA OPERACIONAL: Eres un asistente ejecutivo para el Centro de Control de Rappi. Tu respuesta debe ser telegráfica, ir directo a la conclusión de negocio y no exceder de 50 palabras. Ve al grano, el equipo de operaciones no tiene tiempo para leer preámbulos.
"""

    # ── Comunicación con la API ────────────────────────────────────────────────

    def send_message(self, api_key: str, messages: List[dict]) -> str:
        """
        Envía los mensajes a la API de Claude y devuelve el texto de respuesta.

        Args:
            api_key:  API key de Anthropic proporcionada por el usuario.
            messages: Historial de mensajes en formato [{role, content}].

        Returns:
            Texto de la respuesta del asistente.

        Raises:
            requests.exceptions.Timeout: Si la API no responde en 30 s.
            ValueError: Si la API devuelve un error de negocio.
        """
        system_prompt = self.build_system_prompt()

        response = requests.post(
            ANTHROPIC_API_URL,
            headers={
                "x-api-key": api_key,
                "anthropic-version": ANTHROPIC_API_VERSION,
                "content-type": "application/json",
            },
            json={
                "model": CLAUDE_MODEL,
                "max_tokens": CLAUDE_MAX_TOKENS,
                "system": system_prompt,
                "messages": messages,
            },
            timeout=30,
        )

        data = response.json()

        if response.status_code != 200:
            error_msg = data.get("error", {}).get("message", "Error de API")
            raise ValueError(error_msg)

        return data["content"][0]["text"]
