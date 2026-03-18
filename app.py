import os
import logging
from flask import Flask, render_template, request, jsonify
import mysql.connector
from mysql.connector import Error

# Configurar logging para que los errores se vean en los logs del servidor
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

# Configuración de conexión a MySQL (se puede ajustar con variables de entorno para despliegue)
db_config = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', ''),
    'database': os.environ.get('DB_NAME', 'agenda_virtual')
}

def get_db_connection():
    """Crea una conexión a la base de datos MySQL"""
    try:
        connection = mysql.connector.connect(**db_config)
        return connection
    except Error as e:
        app.logger.exception("Error al conectar a MySQL")
        return None

@app.route('/')
def index():
    """Ruta principal que muestra la página de inicio"""
    return render_template('ejemplo.html')

@app.route('/api/eventos', methods=['GET'])
def get_eventos():
    """Obtiene todas las citas de la agenda"""
    connection = get_db_connection()
    if connection is None:
        return jsonify([]), 200
    
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM citas ORDER BY fecha ASC, hora ASC")
        resultado = cursor.fetchall()
        
        # Convertir objetos no serializables a strings
        for cita in resultado:
            if 'fecha' in cita and cita['fecha']:
                cita['fecha'] = cita['fecha'].isoformat()
            if 'hora' in cita and cita['hora']:
                # Convertir timedelta a string HH:MM:SS
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
    except Error as e:
        app.logger.exception("Error al cargar eventos")
        return jsonify([]), 200

@app.route('/api/eventos', methods=['POST'])
def crear_evento():
    """Crea una nueva cita en la agenda"""
    connection = get_db_connection()
    if connection is None:
        return jsonify({'error': 'No se pudo conectar a la base de datos'}), 500
    
    try:
        data = request.get_json()
        cursor = connection.cursor()
        
        query = """INSERT INTO citas (fecha, hora, nombre_completo, telefono, asunto, zona, atendido)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)"""
        cursor.execute(query, (
            data.get('fecha'),
            data.get('hora'),
            data.get('nombre_completo'),
            data.get('telefono'),
            data.get('asunto'),
            data.get('zona'),
            data.get('atendido', 'no')  # Por defecto 'no'
        ))
        
        connection.commit()
        cita_id = cursor.lastrowid
        cursor.close()
        connection.close()
        return jsonify({'id': cita_id, 'message': 'Cita creada correctamente'}), 201
    except Error as e:
        app.logger.exception("Error al crear evento")
        return jsonify({'error': str(e)}), 500

@app.route('/api/eventos/<int:evento_id>', methods=['DELETE'])
def eliminar_evento(evento_id):
    """Elimina una cita de la agenda"""
    connection = get_db_connection()
    if connection is None:
        return jsonify({'error': 'No se pudo conectar a la base de datos'}), 500
    
    try:
        cursor = connection.cursor()
        cursor.execute("DELETE FROM citas WHERE id = %s", (evento_id,))
        connection.commit()
        cursor.close()
        connection.close()
        return jsonify({'message': 'Cita eliminada correctamente'}), 200
    except Error as e:
        app.logger.exception("Error al eliminar evento")
        return jsonify({'error': str(e)}), 500

@app.route('/api/eventos/<int:evento_id>', methods=['PUT'])
def actualizar_evento(evento_id):
    """Actualiza una cita existente (por ejemplo, marcar como atendido)"""
    connection = get_db_connection()
    if connection is None:
        return jsonify({'error': 'No se pudo conectar a la base de datos'}), 500

    try:
        data = request.get_json() or {}
        # Solo actualizamos los campos permitidos
        campos_validos = {}
        if 'atendido' in data:
            campos_validos['atendido'] = data.get('atendido')

        if not campos_validos:
            return jsonify({'error': 'No se proporcionaron campos válidos para actualizar'}), 400

        set_parts = ', '.join([f"{k} = %s" for k in campos_validos.keys()])
        valores = list(campos_validos.values())
        valores.append(evento_id)

        cursor = connection.cursor()
        cursor.execute(f"UPDATE citas SET {set_parts} WHERE id = %s", valores)
        connection.commit()
        cursor.close()
        connection.close()
        return jsonify({'message': 'Cita actualizada correctamente'}), 200
    except Error as e:
        app.logger.exception("Error al actualizar evento")
        return jsonify({'error': str(e)}), 500

@app.route('/api/saludo', methods=['GET'])
def saludo():
    """Ruta de prueba simple"""
    return jsonify({'mensaje': 'Hola desde Flask!'})

if __name__ == '__main__':
    # Ejecuta la aplicación en modo debug
    # Escucha en todas las interfaces para que herramientas como ngrok puedan conectarse.
    # También permite cambiar el puerto mediante la variable de entorno PORT.
    import os
    puerto = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=puerto)
