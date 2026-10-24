from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import csv
import io

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

# Ruta inicial (Te llevará al Login)
@app.route('/')
def home():
    return redirect(url_for('login'))

# Ruta del Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        password = request.form['password']
        
        # Aquí puedes poner un usuario y contraseña fijo por ahora
        if usuario == "admin" and password == "1234":
            session['usuario'] = usuario
            return redirect(url_for('principal'))
        else:
            return "Usuario o contraseña incorrectos. <a href='/login'>Volver</a>"
            
    return render_template('login.html')
#-----------------------------------------------------------------------------

# Ruta de la página principal (Menú con pestañas)
@app.route('/principal')
def principal():
    if 'usuario' not in session:
        return redirect(url_for('login'))
        
    # Consultamos todos los alumnos de la base de datos
    lista_alumnos = Alumno.query.all()
    return render_template('index.html', alumnos=lista_alumnos)
#---------------------------------------------------------------------------------------------------


# ----------------  Ruta para importar alumnos desde un archivo CSV ---------------------------------
@app.route('/importar_alumnos', methods=['GET', 'POST'])
def importar_alumnos():
    if 'usuario' not in session:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        if 'archivo_csv' not in request.files:
            return "No se seleccionó ningún archivo. <a href='javascript:history.back()'>Volver</a>"
            
        archivo = request.files['archivo_csv']
        
        if archivo.filename == '':
            return "El archivo no tiene nombre. <a href='javascript:history.back()'>Volver</a>"
            
        if archivo and archivo.filename.endswith('.csv'):
            # Leemos el archivo decodificándolo en UTF-8
            stream = io.StringIO(archivo.stream.read().decode("utf-8"), newline=None)
            csv_reader = csv.reader(stream)
            
            # Opcional: Si tu CSV tiene cabecera (Título en la primera línea), la saltamos
            next(csv_reader, None) 
            
            registros_agregados = 0
            errores = []
            
            for fila in csv_reader:
                # Suponemos el orden de columnas en el CSV: 
                # [0] Apellido, [1] Nombre, [2] DNI, [3] Sexo, [4] Fecha Nacimiento (AAAA-MM-DD o DD/MM/AAAA)
                if len(fila) < 3:
                    continue
                    
                apellido_limpio = fila[0].strip().title()
                nombre_limpio = fila[1].strip().title()
                dni_limpio = fila[2].replace('.', '').strip()
                sexo_limpio = fila[3].strip() if len(fila) > 3 else 'Otro'
                fecha_texto = fila[4].strip() if len(fila) > 4 else ''
                
                # Validamos el DNI con la misma regla estricta
                if not dni_limpio.isdigit() or not (7 <= len(dni_limpio) <= 8):
                    continue # Salta los registros con DNI inválido para no romper la base
                
                # Verificamos si el DNI ya existe para no duplicarlo
                existe = Alumno.query.filter_by(dni=dni_limpio).first()
                if existe:
                    continue
                
                # Creamos el objeto alumno
                nuevo = Alumno(
                    apellido=apellido_limpio,
                    nombre=nombre_limpio,
                    dni=dni_limpio,
                    sexo=sexo_limpio,
                    fecha_nacimiento=parsear_fecha(fecha_texto)
                )
                db.session.add(nuevo)
                registros_agregados += 1
                
            db.session.commit()
            return f"¡Importación exitosa! Se agregaron {registros_agregados} alumnos nuevos a la base de datos. <a href='{url_for('principal')}'>Volver al inicio</a>"
            
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
            return "Error: El DNI debe contener solo números (entre 7 y 8 dígitos). <a href='javascript:history.back()'>Volver</a>"

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
            return "Error: El DNI debe contener solo números (entre 7 y 8 dígitos). <a href='javascript:history.back()'>Volver</a>"
    
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

if __name__ == '__main__':
    app.run(debug=True)