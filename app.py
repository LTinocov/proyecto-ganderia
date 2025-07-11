from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify, session
import sqlite3
from datetime import datetime, timedelta
import os
import pandas as pd
import re

app = Flask(__name__)
app.secret_key = 'clave_secreta_super_segura'

def obtener_conexion():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def inicializar_base_de_datos():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        tipo TEXT NOT NULL CHECK(tipo IN ('administrador', 'trabajador')),
        codigo TEXT NOT NULL UNIQUE
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS reportes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo_usuario TEXT NOT NULL,
        codigo_ganado TEXT NOT NULL,
        fecha TEXT NOT NULL,
        hora TEXT NOT NULL,
        semana TEXT NOT NULL,
        UNIQUE(codigo_usuario, codigo_ganado, semana)
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS reportes_semanales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo_usuario TEXT NOT NULL,
        codigo_ganado TEXT NOT NULL,
        fecha TEXT NOT NULL,
        hora TEXT NOT NULL,
        semana TEXT NOT NULL
    )''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tareas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        tiempo_estimado TEXT NOT NULL,
        instrucciones TEXT NOT NULL,
        dias_asignados TEXT NOT NULL,
        horas TEXT NOT NULL,
        semana_asignacion TEXT NOT NULL
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS asignaciones_tareas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_tarea INTEGER NOT NULL,
        codigo_usuario TEXT NOT NULL,
        fecha_asignacion TEXT NOT NULL,
        estado TEXT NOT NULL CHECK(estado IN ('pendiente', 'en_progreso', 'completada', 'pausada')),
        hora_inicio TEXT,
        hora_fin TEXT,
        tiempo_total TEXT,
        FOREIGN KEY(id_tarea) REFERENCES tareas(id)
    )''')

    usuarios = [
        ('Alexandra Tenorio', 'administrador', '1955'),
        ('Luis Tinoco', 'administrador', '8863'),
        ('Jose Tenorio', 'administrador', '7632'),
        ('Ivannia Obando', 'administrador', '4481'),
        ('Don Cecil Alfaro', 'administrador', '1174'),
        ('Raul Aguilar', 'trabajador', '2014'),
        ('Josue Aguilar', 'trabajador', '5498'),
        ('Oscar Aguilar', 'trabajador', '3240'),
        ('Armando Cerdas', 'trabajador', '9549'),
        ('Cesar González', 'trabajador', '2218'),
        ('Tayra Jimenez', 'trabajador', '0251'),
        ('Cristopher Mora', 'trabajador', '3300'),
        ('Carlos Obando', 'trabajador', '4832'),
        ('Luis Obando', 'trabajador', '5190'),
        ('Andres Perez', 'trabajador', '9383'),
        ('Daniel Perez', 'trabajador', '7224'),
        ('Adrian Rojas', 'trabajador', '8782'),
        ('Jose Serrano', 'trabajador', '9010'),
        ('Francisco Solano', 'trabajador', '1314'),
        ('Aaron Solano', 'trabajador', '1010')
    ]
    
    cursor.executemany('INSERT OR IGNORE INTO usuarios (nombre, tipo, codigo) VALUES (?, ?, ?)', usuarios)
    
    conn.commit()
    conn.close()

def obtener_semana(fecha):
    dias_para_viernes = (fecha.weekday() - 4) % 7
    inicio_semana = fecha - timedelta(days=dias_para_viernes)
    return inicio_semana.strftime('%Y-%m-%d')

def mover_reportes_semanales():
    conn = obtener_conexion()
    try:
        hoy = datetime.now()
        dias_para_viernes = (hoy.weekday() - 4) % 7
        viernes_actual = hoy - timedelta(days=dias_para_viernes)
        
        conn.execute('''
            INSERT INTO reportes_semanales 
            SELECT * FROM reportes 
            WHERE fecha < ?
        ''', (viernes_actual.strftime('%Y-%m-%d'),))
        
        conn.execute('DELETE FROM reportes WHERE fecha < ?', (viernes_actual.strftime('%Y-%m-%d'),))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error al mover reportes: {e}")
    finally:
        conn.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    codigo = request.form.get('codigo', '').strip()
    
    conn = obtener_conexion()
    try:
        usuario = conn.execute(
            'SELECT codigo, nombre, tipo FROM usuarios WHERE codigo = ?', 
            (codigo,)
        ).fetchone()
        
        if not usuario:
            flash('Código incorrecto', 'error')
            return redirect(url_for('index'))
            
        # Guardar información en la sesión
        session['user_code'] = usuario['codigo']
        session['user_name'] = usuario['nombre']
        session['user_type'] = usuario['tipo'].lower()  # Almacenar en minúsculas
        
        if usuario['tipo'].lower() == 'trabajador':
            return redirect(url_for('trabajador', codigo_usuario=usuario['codigo']))
        return redirect(url_for('administrador'))
    except Exception as e:
        flash(f'Error al iniciar sesión: {str(e)}', 'error')
        return redirect(url_for('index'))
    finally:
        conn.close()
@app.route('/trabajador/<codigo_usuario>', methods=['GET', 'POST'])
def trabajador(codigo_usuario):
    conn = obtener_conexion()
    fecha_actual = datetime.now().strftime('%Y-%m-%d')
    
    try:
        dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        dia_actual = dias_semana[datetime.now().weekday()]
        usuario = conn.execute(
            'SELECT nombre FROM usuarios WHERE codigo = ?', 
            (codigo_usuario,)
        ).fetchone()
        
        if not usuario:
            flash('Usuario no encontrado', 'error')
            return redirect(url_for('index'))
        
        reportes_diarios = conn.execute(
            'SELECT COUNT(*) FROM reportes WHERE codigo_usuario = ? AND fecha = ?',
            (codigo_usuario, fecha_actual)
        ).fetchone()[0]

        tareas_asignadas = conn.execute('''
            SELECT 
                a.id,
                t.nombre,
                t.instrucciones,
                t.tiempo_estimado,
                a.estado,
                a.hora_inicio,
                a.hora_fin,
                a.tiempo_total
            FROM asignaciones_tareas a
            JOIN tareas t ON a.id_tarea = t.id
            WHERE a.codigo_usuario = ? 
            AND date(a.fecha_asignacion) = date('now')
            AND t.dias_asignados LIKE '%' || ? || '%'
            ORDER BY a.estado DESC, t.nombre ASC
        ''', (codigo_usuario, dia_actual)).fetchall()

        if request.method == 'POST':
            codigo_ganado = request.form.get('codigo_ganado', '').strip().upper()
            
            if not re.match(r'^[A-Za-z0-9\-]{1,6}$', codigo_ganado):
                flash('El código debe contener máximo 6 caracteres (letras, números o guiones)', 'error')
                return redirect(url_for('trabajador', codigo_usuario=codigo_usuario))
            
            semana_actual = obtener_semana(datetime.now())
            
            try:
                existe = conn.execute('''
                    SELECT 1 FROM reportes 
                    WHERE codigo_usuario = ? 
                    AND codigo_ganado = ?
                    AND semana = ?
                ''', (codigo_usuario, codigo_ganado, semana_actual)).fetchone()
                
                if existe:
                    flash('Ya reportaste este animal esta semana', 'error')
                    return redirect(url_for('trabajador', codigo_usuario=codigo_usuario))
                
                conn.execute('''
                    INSERT INTO reportes 
                    (codigo_usuario, codigo_ganado, fecha, hora, semana)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    codigo_usuario,
                    codigo_ganado,
                    fecha_actual,
                    datetime.now().strftime('%H:%M:%S'),
                    semana_actual
                ))
                conn.commit()
                flash('¡Reporte registrado exitosamente!', 'success')
                reportes_diarios += 1
                
            except sqlite3.Error as e:
                conn.rollback()
                flash(f'Error al registrar el reporte: {str(e)}', 'error')

    except Exception as e:
        flash(f'Error en el sistema: {str(e)}', 'error')
    finally:
        conn.close()
            
    return render_template('trabajador.html',
                         codigo_usuario=codigo_usuario,
                         nombre_usuario=usuario['nombre'],
                         reportes_diarios=reportes_diarios,
                         tareas_asignadas=tareas_asignadas)


@app.route('/administrador')
def administrador():
    if 'user_code' not in session or 'user_type' not in session:
        flash('Debes iniciar sesión primero', 'error')
        return redirect(url_for('index'))
    
    # Verificar si el usuario es administrador
    if session['user_type'].lower() != 'administrador':  # Convertir a minúsculas para comparación
        flash('Acceso denegado: no tienes privilegios de administrador', 'error')
        return redirect(url_for('index'))
    
    conn = obtener_conexion()
    try:
        admin = conn.execute('SELECT nombre FROM usuarios WHERE codigo = ?', (session['user_code'],)).fetchone()
        
        if not admin:
            flash('Usuario no encontrado', 'error')
            return redirect(url_for('index'))
        
        trabajadores = conn.execute('''
            SELECT u.*, COUNT(r.id) as total_reportes 
            FROM usuarios u
            LEFT JOIN reportes r ON u.codigo = r.codigo_usuario
            WHERE u.tipo = 'trabajador'
            GROUP BY u.id
            ORDER BY total_reportes DESC, u.nombre ASC
        ''').fetchall()

        reportes = conn.execute('''
            SELECT r.*, u.nombre 
            FROM reportes r
            JOIN usuarios u ON r.codigo_usuario = u.codigo
        ''').fetchall()

        semanas = conn.execute('''
            SELECT DISTINCT semana 
            FROM reportes_semanales 
            ORDER BY substr(semana, 1, 10) DESC
        ''').fetchall()
        
        tareas = conn.execute('SELECT * FROM tareas').fetchall()
        asignaciones = conn.execute('''
            SELECT t.nombre, a.*, u.nombre as nombre_usuario 
            FROM asignaciones_tareas a
            JOIN tareas t ON a.id_tarea = t.id
            JOIN usuarios u ON a.codigo_usuario = u.codigo
        ''').fetchall()

        reportes_semanales = conn.execute('''
            SELECT r.*, u.nombre 
            FROM reportes_semanales r
            JOIN usuarios u ON r.codigo_usuario = u.codigo
        ''').fetchall()
        tareas_semanales = conn.execute('''
            SELECT 
                t.semana_asignacion as semana,
                GROUP_CONCAT(DISTINCT t.dias_asignados) as dias,
                GROUP_CONCAT(DISTINCT t.nombre) as nombres_tareas,
                COUNT(DISTINCT t.id) as total_tareas,
                COUNT(DISTINCT a.id) as total_asignaciones
            FROM tareas t
            LEFT JOIN asignaciones_tareas a ON t.id = a.id_tarea
            GROUP BY t.semana_asignacion
            ORDER BY t.semana_asignacion DESC
        ''').fetchall()

        # Obtener detalles de tareas por semana
        tareas_detalle = {}
        for semana in tareas_semanales:
            detalles = conn.execute('''
                SELECT 
                    t.id,
                    t.nombre,
                    t.tiempo_estimado,
                    t.dias_asignados,
                    t.horas,
                    GROUP_CONCAT(u.nombre, ', ') as trabajadores
                FROM tareas t
                JOIN asignaciones_tareas a ON t.id = a.id_tarea
                JOIN usuarios u ON a.codigo_usuario = u.codigo
                WHERE t.semana_asignacion = ?
                GROUP BY t.id
            ''', (semana['semana'],)).fetchall()
            tareas_detalle[semana['semana']] = detalles

        
    finally:
        conn.close()
    
    return render_template('administrador.html',
                         nombre_admin=admin['nombre'],
                         trabajadores=trabajadores,
                         tareas_semanales=tareas_semanales,
                         tareas_detalle=tareas_detalle,
                         reportes=reportes,
                         semanas=semanas,
                         tareas=tareas,
                         asignaciones=asignaciones,
                         reportes_semanales=reportes_semanales)

@app.route('/agregar_trabajador', methods=['POST'])
def agregar_trabajador():
    nombre = request.form.get('nombre', '').strip()
    codigo = request.form.get('codigo', '').strip()

    if not nombre or not codigo:
        flash('Todos los campos son obligatorios', 'error')
        return redirect(url_for('administrador'))

    conn = obtener_conexion()
    try:
        existe = conn.execute(
            'SELECT id FROM usuarios WHERE codigo = ?', 
            (codigo,)
        ).fetchone()

        if existe:
            flash('El código ya está en uso', 'error')
            return redirect(url_for('administrador'))

        conn.execute(
            'INSERT INTO usuarios (nombre, tipo, codigo) VALUES (?, ?, ?)',
            (nombre, 'trabajador', codigo)
        )
        conn.commit()
        flash('Trabajador agregado exitosamente', 'success')
    except sqlite3.Error as e:
        flash(f'Error al agregar trabajador: {e}', 'error')
    finally:
        conn.close()

    return redirect(url_for('administrador'))
@app.route('/eliminar_tarea/<int:tarea_id>')
def eliminar_tarea(tarea_id):
    conn = obtener_conexion()
    try:
        # Eliminar primero las asignaciones relacionadas
        conn.execute('DELETE FROM asignaciones_tareas WHERE id_tarea = ?', (tarea_id,))
        # Luego eliminar la tarea
        conn.execute('DELETE FROM tareas WHERE id = ?', (tarea_id,))
        conn.commit()
        flash('Tarea eliminada correctamente', 'success')
    except sqlite3.Error as e:
        conn.rollback()
        flash(f'Error al eliminar tarea: {str(e)}', 'error')
    finally:
        conn.close()
    return redirect(url_for('administrador'))
@app.route('/eliminar_semana_tareas/<semana>')
def eliminar_semana_tareas(semana):
    conn = obtener_conexion()
    try:
        # Primero obtener los IDs de las tareas de esta semana
        tareas = conn.execute('SELECT id FROM tareas WHERE semana_asignacion = ?', (semana,)).fetchall()
        
        # Eliminar asignaciones relacionadas
        for tarea in tareas:
            conn.execute('DELETE FROM asignaciones_tareas WHERE id_tarea = ?', (tarea['id'],))
        
        # Eliminar las tareas de la semana
        conn.execute('DELETE FROM tareas WHERE semana_asignacion = ?', (semana,))
        
        conn.commit()
        flash(f'Todas las tareas de la semana {semana} han sido eliminadas', 'success')
    except sqlite3.Error as e:
        conn.rollback()
        flash(f'Error al eliminar tareas de la semana: {str(e)}', 'error')
    finally:
        conn.close()
    return redirect(url_for('administrador'))
@app.route('/eliminar_asignacion/<int:asignacion_id>')
def eliminar_asignacion(asignacion_id):
    conn = obtener_conexion()
    try:
        conn.execute('DELETE FROM asignaciones_tareas WHERE id = ?', (asignacion_id,))
        conn.commit()
        flash('Asignación eliminada correctamente', 'success')
    except sqlite3.Error as e:
        conn.rollback()
        flash(f'Error al eliminar asignación: {str(e)}', 'error')
    finally:
        conn.close()
    return redirect(url_for('administrador'))

@app.route('/exportar_tareas_semana_excel/<semana>')
def exportar_tareas_semana_excel(semana):
    conn = obtener_conexion()
    try:
        tareas = conn.execute('''
            SELECT 
                t.nombre AS tarea,
                t.tiempo_estimado,
                t.dias_asignados,
                t.horas,
                GROUP_CONCAT(u.nombre, ', ') AS trabajadores
            FROM tareas t
            JOIN asignaciones_tareas a ON t.id = a.id_tarea
            JOIN usuarios u ON a.codigo_usuario = u.codigo
            WHERE t.semana_asignacion = ?
            GROUP BY t.id
        ''', (semana,)).fetchall()
        
        df = pd.DataFrame(tareas, columns=[
            'Tarea',
            'Tiempo Estimado',
            'Días Asignados',
            'Horario',
            'Trabajadores'
        ])
        
        nombre_archivo = f"tareas_semana_{semana}.xlsx"
        df.to_excel(nombre_archivo, index=False)
        
        return send_file(nombre_archivo, as_attachment=True)
    finally:
        conn.close()
@app.route('/exportar_excel/<semana>')
def exportar_excel(semana):
    conn = obtener_conexion()
    try:
        reportes = conn.execute('''
            SELECT r.fecha, r.hora, u.nombre as trabajador, r.codigo_ganado 
            FROM reportes_semanales r
            JOIN usuarios u ON r.codigo_usuario = u.codigo
            WHERE r.semana = ?
        ''', (semana,)).fetchall()
        
        df = pd.DataFrame(reportes, columns=['Fecha', 'Hora', 'Trabajador', 'Código Animal'])
        nombre_archivo = f"reportes_semana_{semana.replace(' ', '_').replace('/', '-')}.xlsx"
        df.to_excel(nombre_archivo, index=False)
        
        return send_file(nombre_archivo, as_attachment=True)
    finally:
        conn.close()

@app.route('/eliminar_reporte/<int:reporte_id>')
def eliminar_reporte(reporte_id):
    conn = obtener_conexion()
    try:
        conn.execute('DELETE FROM reportes WHERE id = ?', (reporte_id,))
        conn.commit()
        flash('Reporte eliminado exitosamente', 'success')
    except sqlite3.Error as e:
        flash('Error al eliminar el reporte', 'error')
    finally:
        conn.close()
    return redirect(url_for('administrador'))

@app.route('/crear_tarea', methods=['POST'])
def crear_tarea():
    if request.method == 'POST':
        nombre = request.form['nombre']
        tiempo_estimado = request.form['tiempo_estimado']
        instrucciones = request.form['instrucciones']
        trabajadores = request.form.getlist('trabajadores')
        dias = request.form.getlist('dias')
        horas = request.form['horas']
        
        conn = obtener_conexion()
        try:
            cursor = conn.cursor()
            
            # Insertar la tarea principal
            cursor.execute('''
                INSERT INTO tareas 
                (nombre, tiempo_estimado, instrucciones, dias_asignados, horas, semana_asignacion)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                nombre, 
                tiempo_estimado, 
                instrucciones, 
                ','.join(dias), 
                horas, 
                obtener_semana(datetime.now())
            ))
            
            id_tarea = cursor.lastrowid
            
            # Asignar la tarea a cada trabajador seleccionado
            for codigo in trabajadores:
                cursor.execute('''
                    INSERT INTO asignaciones_tareas 
                    (id_tarea, codigo_usuario, fecha_asignacion, estado)
                    VALUES (?, ?, date('now'), ?)
                ''', (id_tarea, codigo, 'pendiente'))
            
            conn.commit()
            flash('Tarea creada y asignada exitosamente', 'success')
        except sqlite3.Error as e:
            conn.rollback()
            flash(f'Error al crear tarea: {str(e)}', 'error')
        finally:
            conn.close()
    
    return redirect(url_for('administrador'))


@app.route('/actualizar_estado_tarea', methods=['POST'])
def actualizar_estado_tarea():
    data = request.get_json()
    asignacion_id = data['asignacion_id']
    nuevo_estado = data['estado']
    
    conn = obtener_conexion()
    try:
        if nuevo_estado == 'en_progreso':
            conn.execute('''
                UPDATE asignaciones_tareas 
                SET estado = ?, hora_inicio = ?
                WHERE id = ?
            ''', (nuevo_estado, datetime.now().strftime('%H:%M:%S'), asignacion_id))
        elif nuevo_estado == 'completada':
            hora_fin = datetime.now().strftime('%H:%M:%S')
            asignacion = conn.execute('SELECT hora_inicio FROM asignaciones_tareas WHERE id = ?', (asignacion_id,)).fetchone()
            inicio = datetime.strptime(asignacion['hora_inicio'], '%H:%M:%S')
            fin = datetime.strptime(hora_fin, '%H:%M:%S')
            diferencia = fin - inicio
            conn.execute('''
                UPDATE asignaciones_tareas 
                SET estado = ?, hora_fin = ?, tiempo_total = ?
                WHERE id = ?
            ''', (nuevo_estado, hora_fin, str(diferencia), asignacion_id))
        else:
            conn.execute('''
                UPDATE asignaciones_tareas 
                SET estado = ?
                WHERE id = ?
            ''', (nuevo_estado, asignacion_id))
        
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
    finally:
        conn.close()

@app.route('/exportar_reporte_semanal/<semana>')
def exportar_reporte_semanal(semana):
    conn = obtener_conexion()
    try:
        reportes = conn.execute('''
            SELECT r.fecha, r.hora, u.nombre as trabajador, r.codigo_ganado 
            FROM reportes_semanales r
            JOIN usuarios u ON r.codigo_usuario = u.codigo
            WHERE r.semana = ?
        ''', (semana,)).fetchall()
        
        df = pd.DataFrame(reportes, columns=['Fecha', 'Hora', 'Trabajador', 'Código Animal'])
        nombre_archivo = f"reporte_{semana.replace(' ', '_').replace('/', '-')}.xlsx"
        df.to_excel(nombre_archivo, index=False)
        
        return send_file(nombre_archivo, as_attachment=True)
    finally:
        conn.close()

@app.route('/exportar_tareas_excel')
def exportar_tareas_excel():
    conn = obtener_conexion()
    try:
        reportes = conn.execute('''
            SELECT 
                t.nombre AS tarea,
                u.nombre AS trabajador,
                a.fecha_asignacion AS fecha,
                a.estado,
                a.hora_inicio,
                a.hora_fin,
                a.tiempo_total,
                t.tiempo_estimado,
                t.dias_asignados,
                t.horas
            FROM asignaciones_tareas a
            JOIN tareas t ON a.id_tarea = t.id
            JOIN usuarios u ON a.codigo_usuario = u.codigo
            WHERE a.fecha_asignacion BETWEEN ? AND ?
        ''', (obtener_inicio_semana(), obtener_fin_semana())).fetchall()
        
        df = pd.DataFrame(reportes, columns=[
            'Tarea',
            'Trabajador',
            'Fecha',
            'Estado',
            'Hora Inicio',
            'Hora Fin',
            'Tiempo Real',
            'Tiempo Estimado',
            'Días Asignados',
            'Horario'
        ])
        
        nombre_archivo = f"tareas_semana_{datetime.now().strftime('%Y-%m-%d')}.xlsx"
        df.to_excel(nombre_archivo, index=False)
        
        return send_file(nombre_archivo, as_attachment=True)
    finally:
        conn.close()

def obtener_inicio_semana():
    hoy = datetime.now()
    return (hoy - timedelta(days=hoy.weekday() + 3)).strftime('%Y-%m-%d')

def obtener_fin_semana():
    return (datetime.strptime(obtener_inicio_semana(), '%Y-%m-%d') + timedelta(days=7)).strftime('%Y-%m-%d')

if __name__ == '__main__':
    if not os.path.exists('database.db'):
        inicializar_base_de_datos()
    mover_reportes_semanales()
    app.run(host='0.0.0.0', port=5000, debug=True)