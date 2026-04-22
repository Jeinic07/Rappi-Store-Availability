"""
app.py — Entry point de la aplicación Flask.
---------------------------------------------------
Responsabilidad única: crear la aplicación, registrar los blueprints
y arrancar el servidor de desarrollo.

No contiene lógica de negocio, queries SQL ni llamadas a APIs externas;
esas responsabilidades están distribuidas en sus capas correspondientes:

    config.py                          → configuración
    database/connection.py             → infraestructura de BD
    repositories/availability_repository.py → acceso a datos
    services/analytics_service.py      → lógica de analítica
    services/chat_service.py           → integración con Claude
    routes/analytics_routes.py         → endpoints /api/* de datos
    routes/chat_routes.py              → endpoint /api/chat

Uso:
    pip install flask flask-cors requests
    python app.py
"""

import os
from flask import Flask, render_template
from flask_cors import CORS

from config import DB_PATH, SERVER_PORT, DEBUG
from routes.analytics_routes import analytics_bp
from routes.chat_routes import chat_bp


def create_app() -> Flask:
    """
    Factory function que construye y configura la aplicación Flask.
    Facilita la creación de instancias para pruebas sin arrancar el servidor.
    """
    app = Flask(__name__, static_folder="static")
    CORS(app)

    # ── Registrar blueprints ───────────────────────────────────────────────────
    app.register_blueprint(analytics_bp)
    app.register_blueprint(chat_bp)

    # ── Frontend ───────────────────────────────────────────────────────────────
    @app.route("/")
    def index():
        return render_template("index.html")

    return app


# Crear la instancia global para que Gunicorn pueda encontrarla como 'app:app'
app = create_app()

if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        print(f"❌ No se encontró la base de datos: {DB_PATH}")
        print("   Ejecuta primero: python normalize_to_sqlite.py")
    else:
        print("✅ Base de datos encontrada:", DB_PATH)
        print("🚀 Servidor corriendo en: http://localhost:5000")
        # Escuchar en 0.0.0.0 es obligatorio para desplegar en Railway
        app.run(host="0.0.0.0", debug=DEBUG, port=SERVER_PORT)
