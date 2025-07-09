from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
import os
from werkzeug.utils import secure_filename
from datetime import datetime
from functools import wraps
from models import db, Personaje, Arma, Invocacion, Planeta, Elemento, Usuario

app = Flask(__name__)
app.secret_key = 'expediente_digital_secret_key'

# Configuración para subida de archivos
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Configuración de la base de datos
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expedientes.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Crear la base de datos si no existe
with app.app_context():
    db.create_all()
    # Crear usuario administrador si no existe
    admin = Usuario.query.filter_by(username='Burs').first()
    if not admin:
        admin = Usuario(username='Burs', email='burs@admin.com', es_admin=True)
        admin.set_password('Hinata9404')
        db.session.add(admin)
        db.session.commit()

# Decoradores para autenticación
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debes iniciar sesión para acceder a esta página', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debes iniciar sesión para acceder a esta página', 'error')
            return redirect(url_for('login'))
        user = Usuario.query.get(session['user_id'])
        if not user or not user.es_admin:
            flash('Acceso denegado. Se requieren permisos de administrador', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def can_edit_personaje(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debes iniciar sesión para acceder a esta página', 'error')
            return redirect(url_for('login'))
        
        user = Usuario.query.get(session['user_id'])
        if not user:
            flash('Usuario no encontrado', 'error')
            return redirect(url_for('login'))
        
        # Los administradores pueden editar cualquier personaje
        if user.es_admin:
            return f(*args, **kwargs)
        
        # Verificar si el personaje pertenece al usuario
        personaje_id = kwargs.get('personaje_id')
        if personaje_id:
            personaje = Personaje.query.get(personaje_id)
            if not personaje:
                flash('Personaje no encontrado', 'error')
                return redirect(url_for('index'))
            
            # Si el personaje no tiene creador asignado, solo los administradores pueden editarlo
            if personaje.creador_id is None:
                flash('Solo los administradores pueden editar personajes sin creador asignado', 'error')
                return redirect(url_for('ver_personaje', personaje_id=personaje_id))
            
            # Si el personaje tiene creador, verificar que sea el usuario actual
            if personaje.creador_id != user.id:
                flash('Solo puedes editar los personajes que has creado', 'error')
                return redirect(url_for('ver_personaje', personaje_id=personaje_id))
        
        return f(*args, **kwargs)
    return decorated_function

# Filtro personalizado para JSON
@app.template_filter('from_json')
def from_json_filter(value):
    if value:
        import json
        try:
            return json.loads(value)
        except:
            return []
    return []

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Página principal con lista de personajes"""
    personajes = Personaje.query.all()
    return render_template('index.html', personajes=personajes)

@app.route('/personaje/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_personaje():
    """Crear un nuevo personaje"""
    # Verificar límite de personajes para usuarios normales
    user = Usuario.query.get(session['user_id'])
    if not user.puede_crear_personaje():
        flash('Has alcanzado el límite de 3 personajes. Solo los administradores pueden crear más.', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        # Obtener datos del formulario
        nombre = request.form.get('nombre')
        dimension = request.form.get('dimension')
        planeta = request.form.get('planeta')
        edad = request.form.get('edad')
        descripcion = request.form.get('descripcion')
        nivel = request.form.get('nivel')
        rango = request.form.get('rango')
        
        # Manejar subida de fotografía (obligatoria)
        if 'foto' not in request.files:
            flash('La fotografía es obligatoria', 'error')
            return redirect(request.url)
        
        file = request.files['foto']
        if file.filename == '':
            flash('No se seleccionó ningún archivo', 'error')
            return redirect(request.url)
        
        if not allowed_file(file.filename):
            flash('Formato de archivo no permitido. Use: PNG, JPG, JPEG, GIF, WEBP', 'error')
            return redirect(request.url)
        
        # Validar que el archivo tenga extensión
        if file.filename and '.' not in file.filename:
            flash('Archivo sin extensión válida', 'error')
            return redirect(request.url)
        
        extension = file.filename.rsplit('.', 1)[1].lower() if file.filename else 'jpg'
        filename = secure_filename(f"personaje_{nombre}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{extension}")
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        foto_path = f'uploads/{filename}'
        
        # Crear nuevo personaje en la base de datos
        nuevo_personaje = Personaje(
            nombre=nombre,
            dimension=dimension,
            planeta=planeta if planeta else None,
            edad=int(edad) if edad else 0,
            descripcion=descripcion,
            nivel=nivel,
            rango=rango,
            foto=foto_path,
            creador_id=user.id
        )
        
        db.session.add(nuevo_personaje)
        db.session.commit()
        
        flash('Personaje creado exitosamente', 'success')
        return redirect(url_for('ver_personaje', personaje_id=nuevo_personaje.id))
    
    return render_template('nuevo_personaje.html')

@app.route('/personaje/<int:personaje_id>')
def ver_personaje(personaje_id):
    """Ver detalles de un personaje específico"""
    personaje = Personaje.query.get_or_404(personaje_id)
    return render_template('ver_personaje.html', personaje=personaje)

@app.route('/personaje/<int:personaje_id>/editar', methods=['GET', 'POST'])
@can_edit_personaje
def editar_personaje(personaje_id):
    """Editar un personaje existente"""
    personaje = Personaje.query.get_or_404(personaje_id)
    
    if request.method == 'POST':
        # Actualizar datos del personaje
        personaje.nombre = request.form.get('nombre')
        personaje.dimension = request.form.get('dimension')
        personaje.planeta = request.form.get('planeta')
        personaje.edad = int(request.form.get('edad'))
        personaje.descripcion = request.form.get('descripcion')
        personaje.nivel = request.form.get('nivel')
        personaje.rango = request.form.get('rango')
        
        # Manejar nueva fotografía (obligatoria)
        if 'foto' not in request.files:
            flash('La fotografía es obligatoria', 'error')
            return redirect(request.url)
        
        file = request.files['foto']
        if file.filename == '':
            flash('No se seleccionó ningún archivo', 'error')
            return redirect(request.url)
        
        if not allowed_file(file.filename):
            flash('Formato de archivo no permitido. Use: PNG, JPG, JPEG, GIF, WEBP', 'error')
            return redirect(request.url)
        
        filename = secure_filename(f"personaje_{personaje.nombre}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{file.filename.rsplit('.', 1)[1].lower()}")
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        personaje.foto = f'uploads/{filename}'
        
        db.session.commit()
        flash('Personaje actualizado exitosamente', 'success')
        return redirect(url_for('ver_personaje', personaje_id=personaje_id))
    
    return render_template('editar_personaje.html', personaje=personaje)

@app.route('/personaje/<int:personaje_id>/eliminar', methods=['POST'])
@can_edit_personaje
def eliminar_personaje(personaje_id):
    """Eliminar un personaje"""
    personaje = Personaje.query.get_or_404(personaje_id)
    db.session.delete(personaje)
    db.session.commit()
    flash('Personaje eliminado exitosamente', 'success')
    return redirect(url_for('index'))

@app.route('/personaje/<int:personaje_id>/arma/agregar', methods=['POST'])
@can_edit_personaje
def agregar_arma(personaje_id):
    """Agregar un arma a un personaje"""
    personaje = Personaje.query.get_or_404(personaje_id)
    
    # Obtener datos del arma
    nombre_arma = request.form.get('nombre_arma')
    descripcion_arma = request.form.get('descripcion_arma')
    rango_arma = request.form.get('rango_arma')
    nivel_arma = request.form.get('nivel_arma')
    
    # Manejar imagen del arma
    imagen_arma_path = ''
    if 'imagen_arma' in request.files:
        file = request.files['imagen_arma']
        if file and allowed_file(file.filename):
            filename = secure_filename(f"arma_{nombre_arma}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{file.filename.rsplit('.', 1)[1].lower()}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            imagen_arma_path = f'uploads/{filename}'
    
    nueva_arma = Arma(
        nombre=nombre_arma,
        descripcion=descripcion_arma,
        rango=rango_arma,
        nivel=nivel_arma,
        imagen=imagen_arma_path,
        personaje_id=personaje_id
    )
    
    db.session.add(nueva_arma)
    db.session.commit()
    
    flash('Arma agregada exitosamente', 'success')
    return redirect(url_for('ver_personaje', personaje_id=personaje_id))

@app.route('/personaje/<int:personaje_id>/invocacion/agregar', methods=['POST'])
@can_edit_personaje
def agregar_invocacion(personaje_id):
    """Agregar una invocación a un personaje"""
    personaje = Personaje.query.get_or_404(personaje_id)
    
    # Obtener datos de la invocación
    nombre_invocacion = request.form.get('nombre_invocacion')
    descripcion_invocacion = request.form.get('descripcion_invocacion')
    
    # Manejar imagen de la invocación
    imagen_invocacion_path = ''
    if 'imagen_invocacion' in request.files:
        file = request.files['imagen_invocacion']
        if file and allowed_file(file.filename):
            filename = secure_filename(f"invocacion_{nombre_invocacion}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{file.filename.rsplit('.', 1)[1].lower()}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            imagen_invocacion_path = f'uploads/{filename}'
    
    nueva_invocacion = Invocacion(
        nombre=nombre_invocacion,
        descripcion=descripcion_invocacion,
        imagen=imagen_invocacion_path,
        personaje_id=personaje_id
    )
    
    db.session.add(nueva_invocacion)
    db.session.commit()
    
    flash('Invocación agregada exitosamente', 'success')
    return redirect(url_for('ver_personaje', personaje_id=personaje_id))

@app.route('/personaje/<int:personaje_id>/arma/<int:arma_id>/eliminar', methods=['POST'])
@can_edit_personaje
def eliminar_arma(personaje_id, arma_id):
    """Eliminar un arma de un personaje"""
    arma = Arma.query.filter_by(id=arma_id, personaje_id=personaje_id).first_or_404()
    db.session.delete(arma)
    db.session.commit()
    flash('Arma eliminada exitosamente', 'success')
    return redirect(url_for('ver_personaje', personaje_id=personaje_id))

@app.route('/personaje/<int:personaje_id>/invocacion/<int:invocacion_id>/eliminar', methods=['POST'])
@can_edit_personaje
def eliminar_invocacion(personaje_id, invocacion_id):
    """Eliminar una invocación de un personaje"""
    invocacion = Invocacion.query.filter_by(id=invocacion_id, personaje_id=personaje_id).first_or_404()
    db.session.delete(invocacion)
    db.session.commit()
    flash('Invocación eliminada exitosamente', 'success')
    return redirect(url_for('ver_personaje', personaje_id=personaje_id))

# Rutas para gestión de planetas
@app.route('/planetas')
def listar_planetas():
    """Listar todos los planetas"""
    planetas = Planeta.query.order_by(Planeta.dimension, Planeta.nombre).all()
    
    # Calcular el número de personajes por planeta
    for planeta in planetas:
        planeta.num_personajes = Personaje.query.filter_by(planeta=planeta.nombre).count()
    
    return render_template('planetas.html', planetas=planetas)

@app.route('/planeta/nuevo', methods=['GET', 'POST'])
@admin_required
def nuevo_planeta():
    """Crear un nuevo planeta"""
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        dimension = request.form.get('dimension')
        descripcion = request.form.get('descripcion')
        
        # Verificar si el planeta ya existe
        planeta_existente = Planeta.query.filter_by(nombre=nombre).first()
        if planeta_existente:
            flash('Ya existe un planeta con ese nombre', 'error')
            return redirect(request.url)
        
        nuevo_planeta = Planeta(
            nombre=nombre,
            dimension=dimension,
            descripcion=descripcion
        )
        
        db.session.add(nuevo_planeta)
        db.session.commit()
        
        flash('Planeta creado exitosamente', 'success')
        return redirect(url_for('listar_planetas'))
    
    return render_template('nuevo_planeta.html')

@app.route('/planeta/<int:planeta_id>/editar', methods=['GET', 'POST'])
@admin_required
def editar_planeta(planeta_id):
    """Editar un planeta existente"""
    planeta = Planeta.query.get_or_404(planeta_id)
    
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        dimension = request.form.get('dimension')
        descripcion = request.form.get('descripcion')
        
        # Verificar si el nombre ya existe en otro planeta
        planeta_existente = Planeta.query.filter_by(nombre=nombre).first()
        if planeta_existente and planeta_existente.id != planeta_id:
            flash('Ya existe un planeta con ese nombre', 'error')
            return redirect(request.url)
        
        planeta.nombre = nombre
        planeta.dimension = dimension
        planeta.descripcion = descripcion
        
        db.session.commit()
        flash('Planeta actualizado exitosamente', 'success')
        return redirect(url_for('listar_planetas'))
    
    # Calcular el número de personajes por planeta
    planeta.num_personajes = Personaje.query.filter_by(planeta=planeta.nombre).count()
    personajes_planeta = Personaje.query.filter_by(planeta=planeta.nombre).all()
    
    return render_template('editar_planeta.html', planeta=planeta, personajes_planeta=personajes_planeta)

@app.route('/planeta/<int:planeta_id>/eliminar', methods=['POST'])
@admin_required
def eliminar_planeta(planeta_id):
    """Eliminar un planeta"""
    planeta = Planeta.query.get_or_404(planeta_id)
    
    # Verificar si hay personajes asociados
    num_personajes = Personaje.query.filter_by(planeta=planeta.nombre).count()
    if num_personajes > 0:
        flash('No se puede eliminar el planeta porque tiene personajes asociados', 'error')
        return redirect(url_for('listar_planetas'))
    
    db.session.delete(planeta)
    db.session.commit()
    flash('Planeta eliminado exitosamente', 'success')
    return redirect(url_for('listar_planetas'))

@app.route('/api/planetas/<dimension>')
def obtener_planetas_por_dimension(dimension):
    """API para obtener planetas por dimensión (para AJAX)"""
    planetas = Planeta.query.filter_by(dimension=dimension).order_by(Planeta.nombre).all()
    return jsonify([{'id': p.id, 'nombre': p.nombre} for p in planetas])

# Rutas para gestión de elementos
@app.route('/elementos')
def listar_elementos():
    """Listar todos los elementos"""
    elementos = Elemento.query.order_by(Elemento.nombre).all()
    return render_template('elementos.html', elementos=elementos)

@app.route('/elemento/nuevo', methods=['GET', 'POST'])
@admin_required
def nuevo_elemento():
    """Crear un nuevo elemento"""
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        descripcion = request.form.get('descripcion')
        
        # Verificar si el elemento ya existe
        elemento_existente = Elemento.query.filter_by(nombre=nombre).first()
        if elemento_existente:
            flash('Ya existe un elemento con ese nombre', 'error')
            return redirect(request.url)
        
        nuevo_elemento = Elemento(
            nombre=nombre,
            descripcion=descripcion
        )
        
        db.session.add(nuevo_elemento)
        db.session.commit()
        
        flash('Elemento creado exitosamente', 'success')
        return redirect(url_for('listar_elementos'))
    
    return render_template('nuevo_elemento.html')

@app.route('/elemento/<int:elemento_id>/eliminar', methods=['POST'])
@admin_required
def eliminar_elemento(elemento_id):
    """Eliminar un elemento"""
    elemento = Elemento.query.get_or_404(elemento_id)
    db.session.delete(elemento)
    db.session.commit()
    flash('Elemento eliminado exitosamente', 'success')
    return redirect(url_for('listar_elementos'))

@app.route('/api/elementos')
def obtener_elementos():
    """API para obtener todos los elementos (para AJAX)"""
    elementos = Elemento.query.order_by(Elemento.nombre).all()
    return jsonify([{'id': e.id, 'nombre': e.nombre} for e in elementos])

@app.route('/personaje/<int:personaje_id>/elementos', methods=['POST'])
@can_edit_personaje
def actualizar_elementos_personaje(personaje_id):
    """Actualizar elementos de un personaje"""
    personaje = Personaje.query.get_or_404(personaje_id)
    elementos_seleccionados = request.form.getlist('elementos')
    
    # Convertir a JSON string
    import json
    personaje.elementos = json.dumps(elementos_seleccionados)
    
    db.session.commit()
    flash('Elementos del personaje actualizados exitosamente', 'success')
    return redirect(url_for('ver_personaje', personaje_id=personaje_id))

# Rutas de autenticación
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Página de inicio de sesión"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = Usuario.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['es_admin'] = user.es_admin
            flash(f'¡Bienvenido, {user.username}!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Usuario o contraseña incorrectos', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Página de registro de usuarios"""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validaciones
        if password != confirm_password:
            flash('Las contraseñas no coinciden', 'error')
            return redirect(request.url)
        
        if Usuario.query.filter_by(username=username).first():
            flash('El nombre de usuario ya existe', 'error')
            return redirect(request.url)
        
        # Verificar email solo si se proporcionó
        if email and Usuario.query.filter_by(email=email).first():
            flash('El email ya está registrado', 'error')
            return redirect(request.url)
        
        # Crear nuevo usuario
        nuevo_usuario = Usuario(username=username, email=email if email else None)
        nuevo_usuario.set_password(password)
        
        db.session.add(nuevo_usuario)
        db.session.commit()
        
        flash('Usuario registrado exitosamente. Ya puedes iniciar sesión', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    """Cerrar sesión"""
    session.clear()
    flash('Has cerrado sesión exitosamente', 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 