"""
routes/chat_routes.py — Blueprint Flask para el endpoint del chatbot.

Responsabilidad única: validar la request HTTP y delegar al ChatService.
No contiene lógica de IA ni acceso a la base de datos.

Principio de segregación de interfaces: completamente independiente
del blueprint de analítica.
"""

import requests
from flask import Blueprint, jsonify, request
from services.chat_service import ChatService

chat_bp = Blueprint("chat", __name__)
_service = ChatService()


@chat_bp.route("/api/chat", methods=["POST"])
def chat():
    """
    Recibe un historial de mensajes y una API key de Anthropic,
    y devuelve la respuesta del asistente.

    Body JSON esperado:
        {
            "api_key": "sk-ant-...",
            "messages": [{"role": "user", "content": "..."}]
        }
    """
    body     = request.get_json(silent=True) or {}
    api_key  = body.get("api_key", "").strip()
    messages = body.get("messages", [])

    if not api_key:
        return jsonify({"error": "Falta la API key de Anthropic"}), 400
    if not messages:
        return jsonify({"error": "No hay mensajes"}), 400

    try:
        reply = _service.send_message(api_key, messages)
        return jsonify({"reply": reply})

    except requests.exceptions.Timeout:
        return jsonify({"error": "Timeout al contactar la API de Anthropic"}), 504
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 502
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
