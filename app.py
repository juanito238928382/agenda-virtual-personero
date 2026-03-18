import psycopg2
import os
import logging
from flask import Flask, render_template, request, jsonify

# Logging
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

# 🔌 Conexión a PostgreSQL (Render usa DATABASE_URL)
def get_db_connection():
    try:
        connection = psycopg2.connect(
            os.environ.get("DATABASE_URL")
        )
        return connection
    except Exception as e:
        app.logger.error(f"❌ Error conexión PostgreSQL: {e}")
        return None


# 🧩 CREAR TABLA AUTOMÁTICAMENTE
def crear_tabla():
    connection = get_db_connection()
    if connection is None:
        return

    try:
        cursor = connection.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS citas (
            id SERIAL PRIMARY KEY,
            fecha DATE,
            hora TIME,
            nombre_completo VARCHAR(255),
            telefono VARCHAR(50),
            asunto VARCHAR(255),
            zona VARCHAR(100),
            atendido VARCHAR(10) DEFAULT 'no',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        connection.commit()
        cursor.close()
        connection.close()

        print("✅ Tabla 'citas' verificada/creada")

    except Exception as e:
        print("❌ Error creando tabla:", e)


# 👉 SE EJECUTA AL INICIAR
crear_tabla()


# ✅ RUTA PRINCIPAL
@app.route('/')
def index():
    return "FUNCIONA 🔥 (Render activo)"


# 🖥️ HTML
@app.route('/agenda')
def agenda():
    return render_template('index.html')


# 📥 OBTENER EVENTOS
@app.route('/api/eventos', methods=['GET'])
def get_eventos():
    connection = get_db_connection()
    if connection is None:
        return jsonify([]), 200

    try:
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM citas ORDER BY fecha ASC, hora ASC")
        columnas = [desc[0] for desc in cursor.description]
        resultado = []

        for fila in cursor.fetchall():
            cita = dict(zip(columnas, fila))

            if cita.get('fecha'):
                cita['fecha'] = cita['fecha'].isoformat()

            if cita.get('hora'):
                cita['hora'] = str(cita['hora'])

            if cita.get('created_at'):
                cita['created_at'] = cita['created_at'].isoformat()

            resultado.append(cita)

        cursor.close()
        connection.close()

        return jsonify(resultado)

    except Exception as e:
        app.logger.exception("Error al cargar eventos")
        return jsonify([]), 200


# ➕ CREAR EVENTO
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
                   VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id"""

        cursor.execute(query, (
            data.get('fecha'),
            data.get('hora'),
            data.get('nombre_completo'),
            data.get('telefono'),
            data.get('asunto'),
            data.get('zona'),
            data.get('atendido', 'no')
        ))

        cita_id = cursor.fetchone()[0]
        connection.commit()

        cursor.close()
        connection.close()

        return jsonify({'id': cita_id, 'message': 'Cita creada'}), 201

    except Exception as e:
        app.logger.exception("Error al crear evento")
        return jsonify({'error': str(e)}), 500


# ❌ ELIMINAR
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

    except Exception as e:
        app.logger.exception("Error al eliminar")
        return jsonify({'error': str(e)}), 500


# ✏️ ACTUALIZAR
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

    except Exception as e:
        app.logger.exception("Error al actualizar")
        return jsonify({'error': str(e)}), 500


# 👋 TEST
@app.route('/api/saludo')
def saludo():
    return jsonify({'mensaje': 'Hola desde Flask en Render 🚀'})


# 🚀 RUN LOCAL
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)