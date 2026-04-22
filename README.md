# Rappi Store Availability Dashboard & Semantic Chatbot

## 🚀 Descripción del Proyecto
Aplicación web enfocada a perfiles operacionales que permite visualizar, analizar y consultar la disponibilidad histórica de tiendas en Rappi. El objetivo es transformar datos técnicos en decisiones de negocio accionables, midiendo el estado general del servicio y calculando las pérdidas económicas derivadas de caídas del sistema.

## ⭐ Características Principales
1. **Índice de Salud Operacional**: KPI compuesto (0-100) que calcula la salud del sistema evaluando la Estabilidad, Confiabilidad y Cobertura.
2. **Simulador de Impacto Financiero**: Herramienta interactiva para calcular los ingresos estimados perdidos (en COP) provocados por eventos de caída, parametrizable con Ticket Promedio y Pedidos por Tienda.
3. **Chatbot Semántico Ejecutivo**: Un asistente de datos impulsado por Anthropic (Claude) ajustado con un prompt estricto para dar respuestas telegráficas (máximo 50 palabras) y operacionales, evitando tecnicismos largos.
4. **Análisis Gráfico Limpio**: Evolución de tiendas, mapas de calor para detectar horas de riesgo y detalle de alertas críticas recientes.
5. **UI/UX Operacional**: Diseño de "Centro de Control" con métricas claras, fondos de alerta y modo claro/oscuro.

## 🛠️ Arquitectura
*   **Backend**: Python con Flask, implementando un patrón de capas limpio (Routes -> Services -> Repositories).
*   **Base de Datos**: SQLite (`availability.db`) consumida directamente sin ORMs pesados para optimizar el rendimiento de queries analíticas largas (hasta 15,000 registros simultáneos).
*   **Frontend**: HTML, CSS (Vanilla) y JavaScript, utilizando `Chart.js` para la visualización de los datos.

## 📋 Requisitos Previos
*   Python 3.8 o superior.
*   Una API Key válida de Anthropic (necesaria exclusivamente para interactuar con el Chatbot).

## 💻 Instrucciones de Instalación y Ejecución

1.  Abre una terminal y posiciónate en el directorio raíz de este repositorio.
2.  *(Opcional pero recomendado)* Crea y activa un entorno virtual:
    ```bash
    # En Windows:
    python -m venv venv
    venv\Scripts\activate

    # En macOS/Linux:
    python3 -m venv venv
    source venv/bin/activate
    ```
3.  Instala las dependencias requeridas (Flask, requests, etc.):
    ```bash
    pip install -r requirements.txt
    ```
4.  Inicia el servidor backend:
    ```bash
    python app.py
    ```
    *(Asegúrate de que el archivo `availability.db` esté en la misma carpeta).*
5.  Abre tu navegador web e ingresa a: **`http://localhost:5000`**

## 🤖 Uso del Chatbot Semántico
Al ingresar a la interfaz web, dirígete a la parte superior derecha. Verás un campo de contraseña etiquetado como **ANTHROPIC KEY**. Pega allí tu clave de API de Anthropic (empieza con `sk-ant-`). 
*Nota de seguridad: Esta clave se maneja puramente desde el cliente en memoria y se envía por cada petición, no queda almacenada de forma persistente en la base de datos.*
