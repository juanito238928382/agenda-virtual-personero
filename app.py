import os
import logging
from flask import Flask, render_template, request, jsonify
import mysql.connector
from mysql.connector import Error

# Logging
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

# Configuración DB (usa variables de entorno en Render)
db_config = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', ''),
    'database': os.environ.get('DB_NAME', 'agenda_virtual')
}

def get_db_connection():
    try:
        connection = mysql.connector.connect(**db_config)
        return connection
    except Error:
        app.logger.error("❌ No se pudo conectar a MySQL")
        return None


# ✅ RUTA PRINCIPAL (IMPORTANTE PARA PROBAR)
@app.route('/')
def index():
    return "FUNCIONA 🔥 (Render activo)"


# 🔹 OJO: ESTA RUTA USA HTML (cuando ya conectes la BD)
@app.route('/agenda')
def agenda():
    return render_template('ejemplo.html')


@app.route('/api/eventos', methods=['GET'])
def get_eventos():
    connection = get_db_connection()
    if connection is None:
        return jsonify([]), 200

    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM citas ORDER BY fecha ASC, hora ASC")
        resultado = cursor.fetchall()

        for cita in resultado:
            if 'fecha' in cita and cita['fecha']:
                cita['fecha'] = cita['fecha'].isoformat()

            if 'hora' in cita and cita['hora']:
                total_seconds = int(cita['hora'].total_seconds())
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                seconds = total_seconds % 60
                cita['hora'] = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

            if 'created_at' in cita and cita['created_at']:
                cita['created_at'] = cita['created_at'].isoformat()

        cursor.close()
        connection.close()
        return jsonify(resultado)

    except Error:
        app.logger.exception("Error al cargar eventos")
        return jsonify([]), 200


@app.route('/api/eventos', methods=['POST'])
def crear_evento():
    connection = get_db_connection()
    if connection is None:
        return jsonify({'error': 'Sin conexión a BD'}), 500

    try:
        data = request.get_json()
        cursor = connection.cursor()

        query = """INSERT INTO citas 
                   (fecha, hora, nombre_completo, telefono, asunto, zona, atendido)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)"""

        cursor.execute(query, (
            data.get('fecha'),
            data.get('hora'),
            data.get('nombre_completo'),
            data.get('telefono'),
            data.get('asunto'),
            data.get('zona'),
            data.get('atendido', 'no')
        ))

        connection.commit()
        cita_id = cursor.lastrowid

        cursor.close()
        connection.close()

        return jsonify({'id': cita_id, 'message': 'Cita creada'}), 201

    except Error as e:
        app.logger.exception("Error al crear evento")
        return jsonify({'error': str(e)}), 500


@app.route('/api/eventos/<int:evento_id>', methods=['DELETE'])
def eliminar_evento(evento_id):
    connection = get_db_connection()
    if connection is None:
        return jsonify({'error': 'Sin conexión a BD'}), 500

    try:
        cursor = connection.cursor()
        cursor.execute("DELETE FROM citas WHERE id = %s", (evento_id,))
        connection.commit()

        cursor.close()
        connection.close()

        return jsonify({'message': 'Cita eliminada'}), 200

    except Error as e:
        app.logger.exception("Error al eliminar")
        return jsonify({'error': str(e)}), 500


@app.route('/api/eventos/<int:evento_id>', methods=['PUT'])
def actualizar_evento(evento_id):
    connection = get_db_connection()
    if connection is None:
        return jsonify({'error': 'Sin conexión a BD'}), 500

    try:
        data = request.get_json() or {}
        campos = {}

        if 'atendido' in data:
            campos['atendido'] = data.get('atendido')

        if not campos:
            return jsonify({'error': 'Nada que actualizar'}), 400

        set_parts = ', '.join([f"{k} = %s" for k in campos.keys()])
        valores = list(campos.values())
        valores.append(evento_id)

        cursor = connection.cursor()
        cursor.execute(f"UPDATE citas SET {set_parts} WHERE id = %s", valores)

        connection.commit()
        cursor.close()
        connection.close()

        return jsonify({'message': 'Actualizado'}), 200

    except Error as e:
        app.logger.exception("Error al actualizar")
        return jsonify({'error': str(e)}), 500


@app.route('/api/saludo')
def saludo():
    return jsonify({'mensaje': 'Hola desde Flask en Render 🚀'})


# ✅ IMPORTANTE PARA RENDER
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)