from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import csv
import io
from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
from flask import send_file
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'clave_secreta_super_segura'  # Necesario para el login

# CONFIGURACIÓN DE LA BASE DE DATOS POSTGRESQL
# Reemplaza 'tu_usuario' y 'tu_contrasena' con los datos que pusiste al instalar PostgreSQL
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:Mibero606487@localhost:5432/escolares'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Definimos el modelo de la tabla alumnos para que Python la entienda
class Alumno(db.Model):
    __tablename__ = 'alumnos'
    id_alumno = db.Column(db.Integer, primary_key=True)
    apellido = db.Column(db.String(100), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    sexo = db.Column(db.String(20))
    dni = db.Column(db.String(20), unique=True, nullable=False)
    cuil = db.Column(db.String(20))
    edad = db.Column(db.Integer)
    fecha_nacimiento = db.Column(db.Date)
    telefono = db.Column(db.String(30))
    correo = db.Column(db.String(150))
    direccion = db.Column(db.String(255))
    localidad = db.Column(db.String(100))
    escuela_anterior = db.Column(db.String(150))
    ape_padre = db.Column(db.String(100))
    dni_padre = db.Column(db.String(20))
    ape_madre = db.Column(db.String(100))
    dni_madre = db.Column(db.String(20))
    ape_tutor = db.Column(db.String(100))
    dni_tutor = db.Column(db.String(20))

class Usuario(db.Model):
    __tablename__ = 'usuario'  # <-- Acá le dice que use la tabla 'usuario' que creaste en pgAdmin

    id = db.Column(db.Integer, primary_key=True)
    usuario = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

class Curso(db.Model):
    __tablename__ = 'cursos'
    
    id_curso = db.Column(db.Integer, primary_key=True)
    nombre_curso = db.Column(db.String(100), nullable=False)
    # Vinculamos con la tabla alumnos usando su clave primaria id_alumno
    id_alumno = db.Column(db.Integer, db.ForeignKey('alumnos.id_alumno'), nullable=False)
    especialidad = db.Column(db.String(100), nullable=False)
    turno = db.Column(db.String(50), nullable=False)
    profesor_titular = db.Column(db.String(100), nullable=False)
    profesor_suplente = db.Column(db.String(100), nullable=True)
    
    # Esto nos permite acceder a los datos del alumno directamente desde el curso (ej: curso.alumno.apellido)
    alumno = db.relationship('Alumno', backref=db.backref('cursos', lazy=True))
# ==========================================
# 2. AQUÍ ES DONDE PONEMOS LAS FUNCIONES AUXILIARES
# ==========================================
def parsear_fecha(texto_fecha):
    if not texto_fecha:
        return None
    try:
        return datetime.strptime(texto_fecha.replace('/', '-'), '%d-%m-%Y').date()
    except ValueError:
        try:
            return datetime.strptime(texto_fecha, '%Y-%m-%d').date()
        except ValueError:
            return None

def formatear_fecha(fecha_obj):
    if not fecha_obj:
        return ''
    return fecha_obj.strftime('%d/%m/%Y')
#-----------------------------------------------------------------------------

# Función para normalizar el texto de nombres y apellidos
def normalizar_texto(texto):
    if not texto:
        return ""
    # Palabras que deben ir en minúscula si están en medio de un apellido
    excepciones = {"de", "del", "la", "las", "los", "y", "da", "dos"}
    
    palabras = texto.strip().lower().split()
    resultado = []
    for i, palabra in enumerate(palabras):
        if palabra in excepciones and i > 0:
            resultado.append(palabra)
        else:
            resultado.append(palabra.capitalize())
    return " ".join(resultado)
#-----------------------------------------------------------------------------
# Clave secreta que manejarán únicamente Dirección y Secretaría
CLAVE_ADMIN_INSTITUCIONAL = "Secretaria2026*" 

# Ruta inicial
@app.route('/')
def home():
    return redirect(url_for('login'))

# Ruta del Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None  # Variable para el mensaje de error
    if request.method == 'POST':
        nombre_usuario = request.form['usuario'].strip()
        password = request.form['password']
        
        # Buscamos el usuario en la base de datos
        user = Usuario.query.filter_by(usuario=nombre_usuario).first()
        
        # Verificamos si existe y si coincide la contraseña
        if user and check_password_hash(user.password, password):
            session['usuario'] = user.usuario
            return redirect(url_for('principal'))
        else:
            error = "Usuario o contraseña incorrectos."
            
    return render_template('login.html', error=error)

# Ruta de Registro con Clave de Autorización
@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    exito = None
    if request.method == 'POST':
        nombre_usuario = request.form['usuario'].strip()
        password = request.form['password']
        admin_code = request.form['admin_code'].strip()
        
        # 1. Validar la clave institucional
        if admin_code != CLAVE_ADMIN_INSTITUCIONAL:
            error = "La clave de Dirección/Secretaría es incorrecta."
        
        # 2. Verificar si el usuario ya existe
        elif Usuario.query.filter_by(usuario=nombre_usuario).first():
            error = "El nombre de usuario ya está registrado."
        
        else:
            # 3. Hashear la contraseña y guardar en la base de datos
            password_encriptada = generate_password_hash(password)
            nuevo_usuario = Usuario(usuario=nombre_usuario, password=password_encriptada)
            
            db.session.add(nuevo_usuario)
            db.session.commit()
            
            exito = "¡Usuario registrado con éxito!"
            
    return render_template('register.html', error=error, exito=exito)
#-----------------------------------------------------------------------------|

# Ruta de la página principal (Menú con pestañas)
@app.route('/principal')
def principal():
    if 'usuario' not in session:
        return redirect(url_for('login'))
        
    # Consultamos todos los alumnos de la base de datos
    lista_alumnos = Alumno.query.order_by(Alumno.apellido.asc(), Alumno.nombre.asc()).all()
    return render_template('index.html', alumnos=lista_alumnos)
#---------------------------------------------------------------------------------------------------


# ----------------  Ruta para importar alumnos desde un archivo CSV ---------------------------------
@app.route('/importar_alumnos', methods=['GET', 'POST'])
def importar_alumnos():
    if 'usuario' not in session:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        if 'archivo_csv' not in request.files or request.files['archivo_csv'].filename == '':
            flash("No se seleccionó ningún archivo CSV válido.", "danger")
            return redirect(url_for('importar_alumnos'))
            
        archivo = request.files['archivo_csv']
        
        if archivo.filename == '':
            return "El archivo no tiene nombre. <a href='javascript:history.back()'>Volver</a>"
            
        if archivo and archivo.filename.endswith('.csv'):
            stream = io.StringIO(archivo.stream.read().decode("utf-8"), newline=None)
            csv_reader = csv.reader(stream)
            
            # Saltamos la cabecera (títulos)
            next(csv_reader, None) 
            
            registros_agregados = 0
            
            for fila in csv_reader:
                if len(fila) < 3:
                    continue
                    
                # 1. Validación estricta de DNI
                dni_ingresado = fila[2].strip() if len(fila) > 2 else ''
                dni_limpio = dni_ingresado.replace('.', '')
                
                if not dni_limpio.isdigit() or not (7 <= len(dni_limpio) <= 8):
                    continue # Salta los registros con DNI inválido
                
                # Verificamos duplicados por DNI
                existe = Alumno.query.filter_by(dni=dni_limpio).first()
                if existe:
                    continue
                
                # 2. NORMALIZACIÓN DE TEXTOS (Primera en mayúscula, resto en minúscula)
                apellido_limpio = fila[0].strip().title() if len(fila) > 0 and fila[0] else ''
                nombre_limpio = fila[1].strip().title() if len(fila) > 1 and fila[1] else ''
                
                # 3. Limpieza de CUIL (quitamos guiones y espacios por si vienen tipeados así)
                cuil_ingresado = fila[3].strip() if len(fila) > 3 else ''
                cuil_limpio = cuil_ingresado.replace('-', '').replace(' ', '')
                
                sexo = fila[4].strip() if len(fila) > 4 else 'Otro'
                edad_val = fila[5].strip() if len(fila) > 5 and fila[5].isdigit() else None
                fecha_texto = fila[6].strip() if len(fila) > 6 else ''
                
                telefono = fila[7].strip() if len(fila) > 7 else ''
                correo = fila[8].strip() if len(fila) > 8 else ''
                
                # Normalizamos localidad y dirección
                localidad = fila[9].strip().title() if len(fila) > 9 and fila[9] else ''
                direccion = fila[10].strip().title() if len(fila) > 10 and fila[10] else ''
                
                escuela_ant = fila[11].strip() if len(fila) > 11 else ''
                
                # Normalizamos apellidos de padres y tutores
                ape_padre = fila[12].strip().title() if len(fila) > 12 and fila[12] else ''
                dni_padre = fila[13].strip().replace('.', '') if len(fila) > 13 else ''
                
                ape_madre = fila[14].strip().title() if len(fila) > 14 and fila[14] else ''
                dni_madre = fila[15].strip().replace('.', '') if len(fila) > 15 else ''
                
                ape_tutor = fila[16].strip().title() if len(fila) > 16 and fila[16] else ''
                dni_tutor = fila[17].strip().replace('.', '') if len(fila) > 17 else ''

                # Creamos el objeto alumno totalmente normalizado
                nuevo = Alumno(
                    apellido=apellido_limpio,
                    nombre=nombre_limpio,
                    dni=dni_limpio,
                    cuil=cuil_limpio,
                    sexo=sexo,
                    edad=edad_val,
                    fecha_nacimiento=parsear_fecha(fecha_texto),
                    telefono=telefono,
                    correo=correo,
                    localidad=localidad,
                    direccion=direccion,
                    escuela_anterior=escuela_ant,
                    ape_padre=ape_padre,
                    dni_padre=dni_padre,
                    ape_madre=ape_madre,
                    dni_madre=dni_madre,
                    ape_tutor=ape_tutor,
                    dni_tutor=dni_tutor
                )
                db.session.add(nuevo)
                registros_agregados += 1
                
            db.session.commit()
           # Usamos flash para enviar el mensaje de éxito a la pantalla principal
            flash(f"¡Importación exitosa! Se procesaron y agregaron {registros_agregados} alumnos correctamente.", "success")
            return redirect(url_for('principal'))
            
    return render_template('importar.html')
# ----------------------------------------------------------------------------------------

# Ruta para ver la ficha detallada de un alumno
@app.route('/alumno/<int:id_alumno>')
def detalle_alumno(id_alumno):
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    # Buscamos el alumno por su ID o mostramos un error 404 si no existe
    alumno = Alumno.query.get_or_404(id_alumno)
   # AQUÍ CONVERTIMOS LA FECHA PARA LA FICHA (DD/MM/AAAA o un guion si está vacía)
    fecha_str = alumno.fecha_nacimiento.strftime('%d/%m/%Y') if alumno.fecha_nacimiento else '-'
    
    # Le pasamos la variable fecha_str a la plantilla
    return render_template('detalle_alumno.html', alumno=alumno, fecha_str=fecha_str)

# Ruta para crear un nuevo alumno
@app.route('/alumno/nuevo', methods=['GET', 'POST'])
def nuevo_alumno():
    if 'usuario' not in session:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        # 1. Validación de DNI (Se hace al empezar el POST)
        dni_ingresado = request.form.get('dni', '').strip()
        dni_limpio = dni_ingresado.replace('.', '')
        
        if not dni_limpio.isdigit() or not (7 <= len(dni_limpio) <= 8):
            error_msg = "El DNI debe contener solo números (entre 7 y 8 dígitos)."
            # Recargamos el formulario pasándole el error y conservando lo que escribió
            return render_template('form_alumno.html', alumno=None, error=error_msg, fecha_str=request.form.get('fecha_nacimiento', ''))
        
        nuevo = Alumno(
            apellido=normalizar_texto(request.form['apellido']),
            nombre=normalizar_texto(request.form['nombre']),
            sexo=request.form['sexo'],
            dni = dni_limpio,
            cuil=request.form['cuil'],
            edad=request.form['edad'] if request.form['edad'] else None,
            fecha_nacimiento=parsear_fecha(request.form['fecha_nacimiento']),
            telefono=request.form['telefono'],
            correo=request.form['correo'],
            direccion=normalizar_texto(request.form['direccion']),
            localidad=normalizar_texto(request.form['localidad']),
            escuela_anterior=normalizar_texto(request.form['escuela_anterior']),
            ape_padre=normalizar_texto(request.form['ape_padre']),
            dni_padre=request.form['dni_padre'],
            ape_madre=normalizar_texto(request.form['ape_madre']),
            dni_madre=request.form['dni_madre'],
            ape_tutor=normalizar_texto(request.form['ape_tutor']),
            dni_tutor=request.form['dni_tutor']
        )
        db.session.add(nuevo)
        db.session.commit()
        return redirect(url_for('principal'))
        
    return render_template('form_alumno.html', alumno=None, fecha_str='')

# Ruta para editar un alumno existente
@app.route('/alumno/editar/<int:id_alumno>', methods=['GET', 'POST'])
def editar_alumno(id_alumno):
    if 'usuario' not in session:
        return redirect(url_for('login'))
        
    alumno = Alumno.query.get_or_404(id_alumno)

    if request.method == 'POST':

        
        # 1. Validación de DNI al modificar
        dni_ingresado = request.form.get('dni', '').strip()
        dni_limpio = dni_ingresado.replace('.', '')
        
        if not dni_limpio.isdigit() or not (7 <= len(dni_limpio) <= 8):
            error_msg = "El DNI debe contener solo números (entre 7 y 8 dígitos)."
            fecha_str_actual = request.form.get('fecha_nacimiento', '')
            return render_template('form_alumno.html', alumno=alumno, error=error_msg, fecha_str=fecha_str_actual)
        
    if request.method == 'POST':
        alumno.apellido = normalizar_texto(request.form['apellido'])
        alumno.nombre = normalizar_texto(request.form['nombre'])
        alumno.sexo = request.form['sexo']
        alumno.dni = dni_limpio
        alumno.cuil = request.form['cuil']
        alumno.edad = request.form['edad'] if request.form['edad'] else None
        alumno.fecha_nacimiento = parsear_fecha(request.form['fecha_nacimiento'])
        alumno.telefono = request.form['telefono']
        alumno.correo = request.form['correo']
        alumno.direccion = normalizar_texto(request.form['direccion'])
        alumno.localidad = normalizar_texto(request.form['localidad'])
        alumno.escuela_anterior = normalizar_texto(request.form['escuela_anterior'])
        alumno.ape_padre = normalizar_texto(request.form['ape_padre'])
        alumno.dni_padre = request.form['dni_padre']
        alumno.ape_madre = normalizar_texto(request.form['ape_madre'])
        alumno.dni_madre = request.form['dni_madre']
        alumno.ape_tutor = normalizar_texto(request.form['ape_tutor'])
        alumno.dni_tutor = request.form['dni_tutor']
        
        db.session.commit()
       # Preparamos la fecha en formato argentino DD/MM/AAAA para que se vea en el input
        fecha_str = alumno.fecha_nacimiento.strftime('%d/%m/%Y') if alumno.fecha_nacimiento else ''
        return render_template('form_alumno.html', alumno=alumno, fecha_str=fecha_str)
        
    return render_template('form_alumno.html', alumno=alumno)

# Ruta para eliminar un alumno
@app.route('/alumno/eliminar/<int:id_alumno>', methods=['POST'])
def eliminar_alumno(id_alumno):
    if 'usuario' not in session:
        return redirect(url_for('login'))
        
    alumno = Alumno.query.get_or_404(id_alumno)
    db.session.delete(alumno)
    db.session.commit()
    return redirect(url_for('principal'))

# ----------------- REPORTE PDF FICHA ALUMNO -------------------------------------------------
@app.route('/alumno/pdf/<int:id_alumno>')
def generar_ficha_pdf(id_alumno):
    if 'usuario' not in session:
        return redirect(url_for('login'))
        
    alumno = Alumno.query.get_or_404(id_alumno)
    
    # 1. Crear las carpetas si no existen
    carpeta = os.path.join('reportes', 'ficha personal')
    os.makedirs(carpeta, exist_ok=True)
    
    nombre_archivo = f"Ficha_{alumno.dni}_{alumno.apellido}.pdf"
    ruta_completa = os.path.join(carpeta, nombre_archivo)
    
    # 2. Configurar el documento (márgenes de 1.5 cm)
    doc = SimpleDocTemplate(
        ruta_completa, 
        pagesize=letter,
        rightMargin=40, leftMargin=40,
        topMargin=40, bottomMargin=40
    )
    elementos = []
    
    # Estilos personalizados
    estilos = getSampleStyleSheet()
    
    # Estilo para títulos de sección con fondo o color destacado
    estilo_titulo_principal = ParagraphStyle(
        'TituloPrincipal',
        parent=estilos['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#1a365d'), # Azul marino institucional
        alignment=1, # Centrado
        spaceAfter=15
    )
    
    estilo_seccion = ParagraphStyle(
        'TituloSeccion',
        parent=estilos['Heading2'],
        fontSize=11,
        textColor=colors.HexColor('#ffffff'), # Texto blanco
        spaceBefore=0,
        spaceAfter=0
    )
    
    estilo_celda = ParagraphStyle(
        'TextoCelda',
        parent=estilos['Normal'],
        fontSize=9.5,
        textColor=colors.HexColor('#2d3748')
    )
    
    estilo_etiqueta = ParagraphStyle(
        'TextoEtiqueta',
        parent=estilos['Normal'],
        fontSize=9.5,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#1a202c')
    )

    # --- ENCABEZADO ---
    elementos.append(Paragraph("SISTEMA ESCOLAR - FICHA PERSONAL", estilo_titulo_principal))
    elementos.append(Spacer(1, 10))

    # Función auxiliar para crear tablas con estilo profesional
    def crear_tabla_seccion(titulo, datos):
        # Fila de título de la sección
        tabla_datos = [[Paragraph(f"<b>{titulo}</b>", estilo_seccion), '']]
        for etiqueta, valor in datos:
            tabla_datos.append([
                Paragraph(etiqueta, estilo_etiqueta),
                Paragraph(str(valor) if valor else '-', estilo_celda)
            ])
            
        t = Table(tabla_datos, colWidths=[150, 384])
        t.setStyle(TableStyle([
            ('SPAN', (0, 0), (1, 0)), # Une las dos columnas para el título de la sección
            ('BACKGROUND', (0, 0), (1, 0), colors.HexColor('#2b6cb0')), # Fondo azul para la cabecera de sección
            ('BOTTOMPADDING', (0, 0), (1, 0), 6),
            ('TOPPADDING', (0, 0), (1, 0), 6),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f7fafc')), # Fondo gris muy claro para las celdas
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e0')), # Bordes grises finos
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
            ('TOPPADDING', (0, 1), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        return t

    # --- SECCIÓN 1: DATOS PERSONALES ---
    fecha_nac = alumno.fecha_nacimiento.strftime('%d/%m/%Y') if alumno.fecha_nacimiento else '-'
    datos_personales = [
        ("Apellido y Nombre:", f"{alumno.apellido}, {alumno.nombre}"),
        ("DNI:", alumno.dni),
        ("CUIL:", alumno.cuil or '-'),
        ("Sexo:", alumno.sexo or '-'),
        ("Edad:", alumno.edad or '-'),
        ("Fecha de Nacimiento:", fecha_nac)
    ]
    elementos.append(crear_tabla_seccion("DATOS PERSONALES", datos_personales))
    elementos.append(Spacer(1, 12))

    # --- SECCIÓN 2: CONTACTO Y UBICACIÓN ---
    datos_contacto = [
        ("Teléfono:", alumno.telefono or '-'),
        ("Correo Electrónico:", alumno.correo or '-'),
        ("Dirección:", alumno.direccion or '-'),
        ("Localidad:", alumno.localidad or '-'),
        ("Escuela Anterior:", alumno.escuela_anterior or '-')
    ]
    elementos.append(crear_tabla_seccion("INFORMACIÓN DE CONTACTO", datos_contacto))
    elementos.append(Spacer(1, 12))

    # --- SECCIÓN 3: FAMILIA / TUTORES ---
    datos_familia = [
        ("Apellido Padre:", alumno.ape_padre or '-'),
        ("DNI Padre:", alumno.dni_padre or '-'),
        ("Apellido Madre:", alumno.ape_madre or '-'),
        ("DNI Madre:", alumno.dni_madre or '-'),
        ("Apellido Tutor:", alumno.ape_tutor or '-'),
        ("DNI Tutor:", alumno.dni_tutor or '-')
    ]
    elementos.append(crear_tabla_seccion("DATOS DE PADRES / TUTORES", datos_familia))

    # Construir el PDF
    doc.build(elementos)
    
    return send_file(ruta_completa, as_attachment=True)
# ------------------------------------------------------------------------------------------------------------

# ----------------------------Creación de cursos y asignación de alumnos a cursos---------------------------------------------
@app.route('/cursos')
def listar_cursos():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    # Consultamos los cursos y los ordenamos por nombre_curso y especialidad,
    # haciendo un 'join' implícito o explícito con la tabla Alumnos
    cursos = Curso.query.join(Alumno).order_by(Curso.nombre_curso, Curso.especialidad).all()
    
    return render_template('cursos.html', cursos=cursos)
# ------------------------------------------------------------------------------------------------------------

# Ruta para crear un nuevo curso
@app.route('/cursos/nuevo', methods=['GET', 'POST'])
def nuevo_curso():
    if request.method == 'POST':
        nombre_curso = request.form['nombre_curso'].strip()
        id_alumno = request.form['id_alumno']
        especialidad = request.form['especialidad'].strip()
        turno = request.form['turno'].strip()
        profesor_titular = request.form['profesor_titular'].strip()
        profesor_suplente = request.form['profesor_suplente'].strip()
        
        # Guardar en la base de datos
        nuevo = Curso(
            nombre_curso=nombre_curso,
            id_alumno=id_alumno,
            especialidad=especialidad,
            turno=turno,
            profesor_titular=profesor_titular,
            profesor_suplente=profesor_suplente if profesor_suplente else None
        )
        db.session.add(nuevo)
        db.session.commit()
        return redirect(url_for('listar_cursos'))
    
    # Pasamos la lista de alumnos ordenados por apellido para seleccionarlos fácilmente
    alumnos = Alumno.query.order_by(Alumno.apellido).all()
    return render_template('form_curso.html', alumnos=alumnos)
#---------------------------------------------------------------------------------------------------

# Ruta para editar un curso existente
@app.route('/cursos/editar/<int:id_curso>', methods=['GET', 'POST'])
def editar_curso(id_curso):
    # Buscamos el curso o devolvemos error 404 si no existe
    curso = Curso.query.get_or_404(id_curso)
    
    if request.method == 'POST':
        curso.nombre_curso = request.form['nombre_curso'].strip()
        curso.id_alumno = request.form['id_alumno']
        curso.especialidad = request.form['especialidad'].strip()
        curso.turno = request.form['turno'].strip()
        curso.profesor_titular = request.form['profesor_titular'].strip()
        
        profesor_suplente = request.form['profesor_suplente'].strip()
        curso.profesor_suplente = profesor_suplente if profesor_suplente else None
        
        db.session.commit()
        return redirect(url_for('listar_cursos'))
    
    # Pasamos el curso actual y la lista de alumnos al formulario
    alumnos = Alumno.query.order_by(Alumno.apellido).all()
    return render_template('form_curso.html', curso=curso, alumnos=alumnos)
# -----------------------------------------------------------------------------------------------------------

# Ruta para eliminar un curso
@app.route('/cursos/eliminar/<int:id_curso>', methods=['POST'])
def eliminar_curso(id_curso):
    curso = Curso.query.get_or_404(id_curso)
    db.session.delete(curso)
    db.session.commit()
    return redirect(url_for('listar_cursos'))
# ------------------------------------------------------------------------------------------------------------

if __name__ == '__main__':
    app.run(debug=True)