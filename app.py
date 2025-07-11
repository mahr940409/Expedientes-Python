import json
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
import os
from werkzeug.utils import secure_filename
from datetime import datetime
from functools import wraps
from models import db, Personaje, Arma, Invocacion, Planeta, Elemento, Usuario, Ranking, SolicitudElemento, SolicitudArma, SolicitudInvocacion, TiendaItem, Compra, Mensaje

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

# Filtro para convertir saltos de línea en HTML
@app.template_filter('nl2br')
def nl2br_filter(value):
    if value:
        return value.replace('\n', '<br>')
    return value

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.before_request
def actualizar_personajes_creados():
    if 'user_id' in session:
        from models import Personaje
        session['personajes_creados'] = Personaje.query.filter_by(creador_id=session['user_id']).count()

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
        limite = user.obtener_limite_personajes()
        precio = user.obtener_precio_siguiente_slot()
        flash(f'Has alcanzado el límite de {limite} personajes. Puedes comprar un slot adicional por {precio} rastamonios o contactar a un administrador para mejorar tu nivel.', 'error')
        return redirect(url_for('comprar_slot_personaje'))
    
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
        
        # Actualizar rankings después de crear personaje
        actualizar_rankings()
        
        # Actualizar contador de personajes en la sesión
        session['personajes_creados'] = Personaje.query.filter_by(creador_id=user.id).count()
        
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
        
        # Actualizar rankings después de editar personaje
        actualizar_rankings()
        
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
    # Actualizar contador de personajes en la sesión
    user = Usuario.query.get(session['user_id'])
    session['personajes_creados'] = Personaje.query.filter_by(creador_id=user.id).count()
    flash('Personaje eliminado exitosamente', 'success')
    return redirect(url_for('index'))

@app.route('/personaje/<int:personaje_id>/cambiar-imagen', methods=['GET', 'POST'])
@can_edit_personaje
def cambiar_imagen_personaje(personaje_id):
    """Cambiar solo la imagen de un personaje"""
    personaje = Personaje.query.get_or_404(personaje_id)
    
    if request.method == 'POST':
        # Manejar subida de nueva fotografía
        if 'foto' not in request.files:
            flash('Debes seleccionar una nueva imagen', 'error')
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
        filename = secure_filename(f"personaje_{personaje.nombre}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{extension}")
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        personaje.foto = f'uploads/{filename}'
        
        db.session.commit()
        
        flash('Imagen del personaje actualizada exitosamente', 'success')
        return redirect(url_for('ver_personaje', personaje_id=personaje_id))
    
    return render_template('cambiar_imagen_personaje.html', personaje=personaje)

@app.route('/personaje/<int:personaje_id>/arma/agregar', methods=['POST'])
@can_edit_personaje
def agregar_arma(personaje_id):
    """Redirigir a solicitud de arma en lugar de agregar directamente"""
    flash('Para agregar armas, debes usar el sistema de solicitudes. Las armas requieren aprobación del administrador.', 'info')
    return redirect(url_for('nueva_solicitud_arma'))

@app.route('/personaje/<int:personaje_id>/invocacion/agregar', methods=['POST'])
@can_edit_personaje
def agregar_invocacion(personaje_id):
    """Redirigir a solicitud de invocación en lugar de agregar directamente"""
    flash('Para agregar invocaciones, debes usar el sistema de solicitudes. Las invocaciones requieren aprobación del administrador.', 'info')
    return redirect(url_for('nueva_solicitud_invocacion'))

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
            descripcion=descripcion,
            es_basico=request.form.get('es_basico') == 'true'
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

# Funciones para el sistema de rankings
def actualizar_rankings():
    """Actualiza las posiciones del ranking global"""
    personajes = Personaje.query.all()
    
    # Calcular poder de todos los personajes
    personajes_con_poder = []
    for personaje in personajes:
        poder = personaje.calcular_poder()
        personajes_con_poder.append((personaje, poder))
    
    # Ordenar por poder (descendente)
    personajes_con_poder.sort(key=lambda x: x[1], reverse=True)
    
    # Actualizar rankings
    Ranking.query.delete()  # Limpiar rankings anteriores
    
    for posicion, (personaje, poder) in enumerate(personajes_con_poder, 1):
        ranking = Ranking(
            personaje_id=personaje.id,
            poder_total=poder,
            posicion=posicion
        )
        db.session.add(ranking)
    
    db.session.commit()

# Rutas para el sistema de rankings
@app.route('/rankings')
def rankings():
    """Página de rankings globales"""
    # Actualizar rankings si no existen
    if Ranking.query.count() == 0:
        actualizar_rankings()
    
    rankings = Ranking.query.order_by(Ranking.posicion).limit(50).all()
    return render_template('rankings.html', rankings=rankings)

@app.route('/rankings/dimension/<dimension>')
def rankings_dimension(dimension):
    """Rankings por dimensión"""
    rankings = db.session.query(Ranking).join(Personaje).filter(
        Personaje.dimension == dimension
    ).order_by(Ranking.posicion).limit(20).all()
    return render_template('rankings_dimension.html', rankings=rankings, dimension=dimension)

@app.route('/api/rankings')
def api_rankings():
    """API para obtener rankings en JSON"""
    # Actualizar rankings si no existen
    if Ranking.query.count() == 0:
        actualizar_rankings()
    
    rankings = Ranking.query.order_by(Ranking.posicion).limit(10).all()
    return jsonify([{
        'posicion': r.posicion,
        'personaje': r.personaje.nombre,
        'poder': r.poder_total,
        'nivel': r.personaje.nivel,
        'dimension': r.personaje.dimension
    } for r in rankings])

@app.route('/actualizar-rankings')
@admin_required
def actualizar_rankings_manual():
    """Actualizar rankings manualmente (solo admin)"""
    actualizar_rankings()
    flash('Rankings actualizados exitosamente', 'success')
    return redirect(url_for('rankings'))

# Rutas para el sistema de solicitudes de elementos
@app.route('/solicitudes')
@login_required
def listar_solicitudes():
    """Listar solicitudes del usuario"""
    user = Usuario.query.get(session['user_id'])
    if user.es_admin:
        # Administradores ven todas las solicitudes
        solicitudes = SolicitudElemento.query.order_by(SolicitudElemento.fecha_solicitud.desc()).all()
    else:
        # Usuarios normales ven solo sus solicitudes
        solicitudes = SolicitudElemento.query.filter_by(usuario_id=user.id).order_by(SolicitudElemento.fecha_solicitud.desc()).all()
    
    return render_template('solicitudes.html', solicitudes=solicitudes)

@app.route('/solicitud/nueva', methods=['GET', 'POST'])
@login_required
def nueva_solicitud():
    """Crear nueva solicitud de elemento"""
    if request.method == 'POST':
        elemento_id = request.form.get('elemento_id')
        personaje_id = request.form.get('personaje_id')
        motivo = request.form.get('motivo')
        
        # Verificar que el personaje pertenece al usuario
        user = Usuario.query.get(session['user_id'])
        personaje = Personaje.query.get(personaje_id)
        
        if not personaje or (not user.es_admin and personaje.creador_id != user.id):
            flash('Personaje no encontrado o no tienes permisos', 'error')
            return redirect(url_for('index'))
        
        # Verificar que no hay una solicitud pendiente para este elemento y personaje
        solicitud_existente = SolicitudElemento.query.filter_by(
            usuario_id=user.id,
            elemento_id=elemento_id,
            personaje_id=personaje_id,
            estado='pendiente'
        ).first()
        
        if solicitud_existente:
            flash('Ya tienes una solicitud pendiente para este elemento y personaje', 'error')
            return redirect(url_for('listar_solicitudes'))
        
        nueva_solicitud = SolicitudElemento(
            usuario_id=user.id,
            elemento_id=elemento_id,
            personaje_id=personaje_id,
            motivo=motivo
        )
        
        db.session.add(nueva_solicitud)
        db.session.commit()
        
        flash('Solicitud enviada exitosamente. El administrador la revisará pronto.', 'success')
        return redirect(url_for('listar_solicitudes'))
    
    # Obtener elementos avanzados y personajes del usuario
    elementos_avanzados = Elemento.query.filter_by(es_basico=False).all()
    user = Usuario.query.get(session['user_id'])
    if user.es_admin:
        personajes = Personaje.query.all()
    else:
        personajes = Personaje.query.filter_by(creador_id=user.id).all()
    
    return render_template('nueva_solicitud.html', elementos=elementos_avanzados, personajes=personajes)

@app.route('/solicitud/<int:solicitud_id>/aprobar', methods=['POST'])
@admin_required
def aprobar_solicitud(solicitud_id):
    """Aprobar una solicitud de elemento"""
    solicitud = SolicitudElemento.query.get_or_404(solicitud_id)
    respuesta = request.form.get('respuesta', 'Solicitud aprobada')
    
    solicitud.estado = 'aprobada'
    solicitud.respuesta_admin = respuesta
    solicitud.fecha_respuesta = datetime.utcnow()
    
    # Agregar el elemento al personaje
    personaje = solicitud.personaje
    elementos_actuales = json.loads(personaje.elementos) if personaje.elementos else []
    elemento = solicitud.elemento
    
    if elemento.nombre not in elementos_actuales:
        elementos_actuales.append(elemento.nombre)
        personaje.elementos = json.dumps(elementos_actuales)
        
        # Actualizar rankings
        actualizar_rankings()
    
    db.session.commit()
    flash('Solicitud aprobada exitosamente', 'success')
    return redirect(url_for('listar_solicitudes'))

@app.route('/solicitud/<int:solicitud_id>/rechazar', methods=['POST'])
@admin_required
def rechazar_solicitud(solicitud_id):
    """Rechazar una solicitud de elemento"""
    solicitud = SolicitudElemento.query.get_or_404(solicitud_id)
    respuesta = request.form.get('respuesta', 'Solicitud rechazada')
    
    solicitud.estado = 'rechazada'
    solicitud.respuesta_admin = respuesta
    solicitud.fecha_respuesta = datetime.utcnow()
    
    db.session.commit()
    flash('Solicitud rechazada', 'success')
    return redirect(url_for('listar_solicitudes'))

@app.route('/api/elementos-disponibles/<int:personaje_id>')
@login_required
def obtener_elementos_disponibles(personaje_id):
    """API para obtener elementos disponibles para un personaje"""
    user = Usuario.query.get(session['user_id'])
    personaje = Personaje.query.get_or_404(personaje_id)
    
    # Verificar permisos
    if not user.es_admin and personaje.creador_id != user.id:
        return jsonify({'error': 'Sin permisos'}), 403
    
    # Elementos básicos siempre disponibles
    elementos_basicos = Elemento.query.filter_by(es_basico=True).all()
    
    # Elementos avanzados que ya tiene el personaje
    elementos_actuales = json.loads(personaje.elementos) if personaje.elementos else []
    elementos_avanzados_actuales = Elemento.query.filter(
        Elemento.es_basico == False,
        Elemento.nombre.in_(elementos_actuales)
    ).all()
    
    # Elementos avanzados solicitados y aprobados
    solicitudes_aprobadas = SolicitudElemento.query.filter_by(
        usuario_id=user.id,
        personaje_id=personaje_id,
        estado='aprobada'
    ).all()
    
    elementos_aprobados = [s.elemento for s in solicitudes_aprobadas]
    
    # Combinar todos los elementos disponibles
    elementos_disponibles = elementos_basicos + elementos_avanzados_actuales + elementos_aprobados
    
    return jsonify([{
        'id': e.id,
        'nombre': e.nombre,
        'es_basico': e.es_basico
    } for e in elementos_disponibles])

# Rutas para el sistema de solicitudes de armas
@app.route('/solicitudes-armas')
@login_required
def listar_solicitudes_armas():
    """Listar solicitudes de armas del usuario"""
    user = Usuario.query.get(session['user_id'])
    if user.es_admin:
        # Administradores ven todas las solicitudes
        solicitudes = SolicitudArma.query.order_by(SolicitudArma.fecha_solicitud.desc()).all()
    else:
        # Usuarios normales ven solo sus solicitudes
        solicitudes = SolicitudArma.query.filter_by(usuario_id=user.id).order_by(SolicitudArma.fecha_solicitud.desc()).all()
    
    return render_template('solicitudes_armas.html', solicitudes=solicitudes)

@app.route('/solicitud-arma/nueva', methods=['GET', 'POST'])
@login_required
def nueva_solicitud_arma():
    """Crear nueva solicitud de arma"""
    if request.method == 'POST':
        personaje_id = request.form.get('personaje_id')
        nombre = request.form.get('nombre')
        descripcion = request.form.get('descripcion')
        rango = request.form.get('rango')
        nivel = request.form.get('nivel')
        motivo = request.form.get('motivo')
        
        # Manejo de imagen
        imagen = 'default_arma.jpg'  # Imagen por defecto
        if 'imagen' in request.files:
            file = request.files['imagen']
            if file and allowed_file(file.filename):
                filename = secure_filename(f"arma_{nombre}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                imagen = filename
        
        # Verificar que el personaje pertenece al usuario
        user = Usuario.query.get(session['user_id'])
        personaje = Personaje.query.get(personaje_id)
        
        if not personaje or (not user.es_admin and personaje.creador_id != user.id):
            flash('Personaje no encontrado o no tienes permisos', 'error')
            return redirect(url_for('index'))
        
        nueva_solicitud = SolicitudArma(
            usuario_id=user.id,
            personaje_id=personaje_id,
            nombre=nombre,
            descripcion=descripcion,
            imagen=imagen,
            rango=rango,
            nivel=nivel,
            motivo=motivo
        )
        
        db.session.add(nueva_solicitud)
        db.session.commit()
        
        flash('Solicitud de arma enviada exitosamente. El administrador la revisará pronto.', 'success')
        return redirect(url_for('listar_solicitudes_armas'))
    
    # Obtener personajes del usuario
    user = Usuario.query.get(session['user_id'])
    if user.es_admin:
        personajes = Personaje.query.all()
    else:
        personajes = Personaje.query.filter_by(creador_id=user.id).all()
    
    return render_template('nueva_solicitud_arma.html', personajes=personajes)

@app.route('/solicitud-arma/<int:solicitud_id>/aprobar', methods=['POST'])
@admin_required
def aprobar_solicitud_arma(solicitud_id):
    """Aprobar una solicitud de arma"""
    solicitud = SolicitudArma.query.get_or_404(solicitud_id)
    respuesta = request.form.get('respuesta', 'Solicitud aprobada')
    
    solicitud.estado = 'aprobada'
    solicitud.respuesta_admin = respuesta
    solicitud.fecha_respuesta = datetime.utcnow()
    
    # Crear la arma y agregarla al personaje
    nueva_arma = Arma(
        nombre=solicitud.nombre,
        descripcion=solicitud.descripcion,
        imagen=solicitud.imagen,
        rango=solicitud.rango,
        nivel=solicitud.nivel,
        personaje_id=solicitud.personaje_id
    )
    
    db.session.add(nueva_arma)
    
    # Actualizar rankings
    actualizar_rankings()
    
    db.session.commit()
    flash('Solicitud de arma aprobada exitosamente', 'success')
    return redirect(url_for('listar_solicitudes_armas'))

@app.route('/solicitud-arma/<int:solicitud_id>/rechazar', methods=['POST'])
@admin_required
def rechazar_solicitud_arma(solicitud_id):
    """Rechazar una solicitud de arma"""
    solicitud = SolicitudArma.query.get_or_404(solicitud_id)
    respuesta = request.form.get('respuesta', 'Solicitud rechazada')
    
    solicitud.estado = 'rechazada'
    solicitud.respuesta_admin = respuesta
    solicitud.fecha_respuesta = datetime.utcnow()
    
    db.session.commit()
    flash('Solicitud de arma rechazada', 'success')
    return redirect(url_for('listar_solicitudes_armas'))

# Rutas para el sistema de solicitudes de invocaciones
@app.route('/solicitudes-invocaciones')
@login_required
def listar_solicitudes_invocaciones():
    """Listar solicitudes de invocaciones del usuario"""
    user = Usuario.query.get(session['user_id'])
    if user.es_admin:
        # Administradores ven todas las solicitudes
        solicitudes = SolicitudInvocacion.query.order_by(SolicitudInvocacion.fecha_solicitud.desc()).all()
    else:
        # Usuarios normales ven solo sus solicitudes
        solicitudes = SolicitudInvocacion.query.filter_by(usuario_id=user.id).order_by(SolicitudInvocacion.fecha_solicitud.desc()).all()
    
    return render_template('solicitudes_invocaciones.html', solicitudes=solicitudes)

@app.route('/solicitud-invocacion/nueva', methods=['GET', 'POST'])
@login_required
def nueva_solicitud_invocacion():
    """Crear nueva solicitud de invocación"""
    if request.method == 'POST':
        personaje_id = request.form.get('personaje_id')
        nombre = request.form.get('nombre')
        descripcion = request.form.get('descripcion')
        rango = request.form.get('rango')
        nivel = request.form.get('nivel')
        motivo = request.form.get('motivo')
        
        # Manejo de imagen
        imagen = 'default_invocacion.jpg'  # Imagen por defecto
        if 'imagen' in request.files:
            file = request.files['imagen']
            if file and allowed_file(file.filename):
                filename = secure_filename(f"invocacion_{nombre}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                imagen = filename
        
        # Verificar que el personaje pertenece al usuario
        user = Usuario.query.get(session['user_id'])
        personaje = Personaje.query.get(personaje_id)
        
        if not personaje or (not user.es_admin and personaje.creador_id != user.id):
            flash('Personaje no encontrado o no tienes permisos', 'error')
            return redirect(url_for('index'))
        
        nueva_solicitud = SolicitudInvocacion(
            usuario_id=user.id,
            personaje_id=personaje_id,
            nombre=nombre,
            descripcion=descripcion,
            imagen=imagen,
            rango=rango,
            nivel=nivel,
            motivo=motivo
        )
        
        db.session.add(nueva_solicitud)
        db.session.commit()
        
        flash('Solicitud de invocación enviada exitosamente. El administrador la revisará pronto.', 'success')
        return redirect(url_for('listar_solicitudes_invocaciones'))
    
    # Obtener personajes del usuario
    user = Usuario.query.get(session['user_id'])
    if user.es_admin:
        personajes = Personaje.query.all()
    else:
        personajes = Personaje.query.filter_by(creador_id=user.id).all()
    
    return render_template('nueva_solicitud_invocacion.html', personajes=personajes)

@app.route('/solicitud-invocacion/<int:solicitud_id>/aprobar', methods=['POST'])
@admin_required
def aprobar_solicitud_invocacion(solicitud_id):
    """Aprobar una solicitud de invocación"""
    solicitud = SolicitudInvocacion.query.get_or_404(solicitud_id)
    respuesta = request.form.get('respuesta', 'Solicitud aprobada')
    
    solicitud.estado = 'aprobada'
    solicitud.respuesta_admin = respuesta
    solicitud.fecha_respuesta = datetime.utcnow()
    
    # Crear la invocación y agregarla al personaje
    nueva_invocacion = Invocacion(
        nombre=solicitud.nombre,
        descripcion=solicitud.descripcion,
        imagen=solicitud.imagen,
        rango=solicitud.rango,
        nivel=solicitud.nivel,
        personaje_id=solicitud.personaje_id
    )
    
    db.session.add(nueva_invocacion)
    
    # Actualizar rankings
    actualizar_rankings()
    
    db.session.commit()
    flash('Solicitud de invocación aprobada exitosamente', 'success')
    return redirect(url_for('listar_solicitudes_invocaciones'))

@app.route('/solicitud-invocacion/<int:solicitud_id>/rechazar', methods=['POST'])
@admin_required
def rechazar_solicitud_invocacion(solicitud_id):
    """Rechazar una solicitud de invocación"""
    solicitud = SolicitudInvocacion.query.get_or_404(solicitud_id)
    respuesta = request.form.get('respuesta', 'Solicitud rechazada')
    
    solicitud.estado = 'rechazada'
    solicitud.respuesta_admin = respuesta
    solicitud.fecha_respuesta = datetime.utcnow()
    
    db.session.commit()
    flash('Solicitud de invocación rechazada', 'success')
    return redirect(url_for('listar_solicitudes_invocaciones'))

@app.route('/tienda')
@login_required
def tienda():
    items = TiendaItem.query.filter_by(disponible=True).all()
    user = Usuario.query.get(session['user_id'])
    personajes = Personaje.query.filter_by(creador_id=user.id).all() if not user.es_admin else Personaje.query.all()
    return render_template('tienda.html', items=items, personajes=personajes)

@app.route('/tienda/comprar', methods=['POST'])
@login_required
def comprar_item():
    personaje_id = request.form.get('personaje_id')
    item_id = request.form.get('item_id')
    cantidad = int(request.form.get('cantidad', 1))
    personaje = Personaje.query.get_or_404(personaje_id)
    item = TiendaItem.query.get_or_404(item_id)
    
    # Verificar si el item está disponible
    if not item.disponible:
        flash('Este item no está disponible para compra.', 'error')
        return redirect(url_for('tienda'))
    
    # Verificar si es un item único y ya fue comprado
    if item.es_unico:
        compras_existentes = Compra.query.filter_by(item_id=item.id).count()
        if compras_existentes > 0:
            flash('Este item único ya ha sido comprado por otro personaje.', 'error')
            return redirect(url_for('tienda'))
    else:
        # Verificar stock para items normales
        if item.stock >= 0:  # Si tiene stock limitado
            if item.stock < cantidad:
                flash(f'No hay suficiente stock. Solo quedan {item.stock} unidades disponibles.', 'error')
                return redirect(url_for('tienda'))
    
    # Verificar límite de 33 items por personaje
    total_items_personaje = Compra.query.filter_by(personaje_id=personaje.id).count()
    if total_items_personaje + cantidad > 33:
        flash(f'No puedes comprar más items. Tu personaje ya tiene {total_items_personaje} items y el límite es 33.', 'error')
        return redirect(url_for('tienda'))
    
    total = item.precio * cantidad
    if personaje.rastamonios < total:
        flash('No tienes suficientes rastamonios para esta compra.', 'error')
        return redirect(url_for('tienda'))
    
    # Realizar la compra
    personaje.rastamonios -= total
    compra = Compra(personaje_id=personaje.id, item_id=item.id, cantidad=cantidad)
    db.session.add(compra)
    
    # Actualizar stock o disponibilidad
    if item.es_unico:
        item.disponible = False
    else:
        # Reducir stock para items normales
        if item.stock >= 0:
            item.stock -= cantidad
            # Si se agota el stock, marcarlo como no disponible
            if item.stock <= 0:
                item.disponible = False
    
    # Actualizar rankings ya que el personaje ganó poder
    actualizar_rankings()
    
    db.session.commit()
    flash(f'¡Compra exitosa! Has adquirido {cantidad}x {item.nombre}.', 'success')
    return redirect(url_for('tienda'))

@app.route('/tienda/compras/<int:personaje_id>')
@login_required
def ver_compras(personaje_id):
    personaje = Personaje.query.get_or_404(personaje_id)
    compras = Compra.query.filter_by(personaje_id=personaje.id).all()
    return render_template('compras.html', personaje=personaje, compras=compras)

# Rutas para administración de la tienda
@app.route('/admin/tienda')
@admin_required
def admin_tienda():
    """Panel de administración de la tienda"""
    items = TiendaItem.query.order_by(TiendaItem.fecha_creacion.desc()).all()
    return render_template('admin_tienda.html', items=items)

@app.route('/admin/tienda/nuevo', methods=['GET', 'POST'])
@admin_required
def nuevo_item_tienda():
    """Crear nuevo item para la tienda"""
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        descripcion = request.form.get('descripcion')
        precio = int(request.form.get('precio'))
        es_unico = request.form.get('es_unico') == 'on'
        stock = int(request.form.get('stock', -1))
        poder_adicional = int(request.form.get('poder_adicional', 0))
        
        # Manejo de imagen
        imagen = None
        if 'imagen' in request.files:
            file = request.files['imagen']
            if file and allowed_file(file.filename):
                filename = secure_filename(f"item_{nombre}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                imagen = f'uploads/{filename}'
        
        nuevo_item = TiendaItem(
            nombre=nombre,
            descripcion=descripcion,
            precio=precio,
            imagen=imagen,
            es_unico=es_unico,
            stock=stock,
            poder_adicional=poder_adicional,
            disponible=True
        )
        
        db.session.add(nuevo_item)
        db.session.commit()
        
        flash('Item agregado a la tienda exitosamente', 'success')
        return redirect(url_for('admin_tienda'))
    
    return render_template('nuevo_item_tienda.html')

@app.route('/admin/tienda/<int:item_id>/editar', methods=['GET', 'POST'])
@admin_required
def editar_item_tienda(item_id):
    """Editar item de la tienda"""
    item = TiendaItem.query.get_or_404(item_id)
    
    if request.method == 'POST':
        item.nombre = request.form.get('nombre')
        item.descripcion = request.form.get('descripcion')
        item.precio = int(request.form.get('precio'))
        item.es_unico = request.form.get('es_unico') == 'on'
        item.stock = int(request.form.get('stock', -1))
        item.poder_adicional = int(request.form.get('poder_adicional', 0))
        item.disponible = request.form.get('disponible') == 'on'
        
        # Manejo de imagen
        if 'imagen' in request.files:
            file = request.files['imagen']
            if file and allowed_file(file.filename):
                filename = secure_filename(f"item_{item.nombre}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                item.imagen = f'uploads/{filename}'
        
        db.session.commit()
        flash('Item actualizado exitosamente', 'success')
        return redirect(url_for('admin_tienda'))
    
    return render_template('editar_item_tienda.html', item=item)

@app.route('/admin/tienda/<int:item_id>/eliminar', methods=['POST'])
@admin_required
def eliminar_item_tienda(item_id):
    """Eliminar item de la tienda"""
    item = TiendaItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash('Item eliminado de la tienda', 'success')
    return redirect(url_for('admin_tienda'))

# Sistema de venta de objetos
@app.route('/personaje/<int:personaje_id>/vender/<int:compra_id>', methods=['GET', 'POST'])
@login_required
def vender_item(personaje_id, compra_id):
    """Vender un item comprado"""
    personaje = Personaje.query.get_or_404(personaje_id)
    compra = Compra.query.get_or_404(compra_id)
    
    # Verificar que la compra pertenece al personaje
    if compra.personaje_id != personaje.id:
        flash('No tienes permisos para vender este item', 'error')
        return redirect(url_for('ver_personaje', personaje_id=personaje_id))
    
    if request.method == 'POST':
        precio_venta = request.form.get('precio_venta')
        
        if not precio_venta or not precio_venta.isdigit():
            flash('Debes ingresar un precio válido', 'error')
            return redirect(url_for('vender_item', personaje_id=personaje_id, compra_id=compra_id))
        
        precio_venta = int(precio_venta)
        
        if precio_venta < 0:
            flash('El precio no puede ser negativo', 'error')
            return redirect(url_for('vender_item', personaje_id=personaje_id, compra_id=compra_id))
        
        # Si es un item único, actualizar el precio y volver a ponerlo disponible
        if compra.item.es_unico:
            compra.item.precio = precio_venta
            compra.item.disponible = True
        else:
            # Para items no únicos, dar rastamonios al personaje y aumentar stock
            personaje.rastamonios += precio_venta
            # Aumentar stock si el item tiene stock limitado
            if compra.item.stock >= 0:
                compra.item.stock += compra.cantidad
                # Si el item estaba agotado, volver a ponerlo disponible
                if not compra.item.disponible and compra.item.stock > 0:
                    compra.item.disponible = True
        
        # Eliminar la compra
        db.session.delete(compra)
        db.session.commit()
        
        if compra.item.es_unico:
            flash(f'Has puesto {compra.item.nombre} en venta por {precio_venta} rastamonios', 'success')
        else:
            flash(f'Has vendido {compra.item.nombre} por {precio_venta} rastamonios', 'success')
        
        return redirect(url_for('ver_personaje', personaje_id=personaje_id))
    
    # GET: mostrar formulario de venta
    return render_template('vender_item.html', personaje=personaje, compra=compra)

# Sistema de Mensajería
@app.route('/mensajes')
@login_required
def mensajes():
    """Página principal de mensajes"""
    user = Usuario.query.get(session['user_id'])
    personajes = Personaje.query.filter_by(creador_id=user.id).all() if not user.es_admin else Personaje.query.all()
    return render_template('mensajes.html', personajes=personajes)

@app.route('/mensajes/<int:personaje_id>')
@login_required
def ver_mensajes(personaje_id):
    """Ver mensajes de un personaje específico"""
    personaje = Personaje.query.get_or_404(personaje_id)
    
    # Verificar permisos
    user = Usuario.query.get(session['user_id'])
    if not user.es_admin and personaje.creador_id != user.id:
        flash('No tienes permisos para ver los mensajes de este personaje', 'error')
        return redirect(url_for('mensajes'))
    
    mensajes_recibidos = Mensaje.query.filter_by(destinatario_id=personaje.id).order_by(Mensaje.fecha_envio.desc()).all()
    mensajes_enviados = Mensaje.query.filter_by(remitente_id=personaje.id).order_by(Mensaje.fecha_envio.desc()).all()
    
    return render_template('ver_mensajes.html', 
                         personaje=personaje, 
                         mensajes_recibidos=mensajes_recibidos,
                         mensajes_enviados=mensajes_enviados)

@app.route('/mensaje/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_mensaje():
    """Enviar un nuevo mensaje"""
    if request.method == 'POST':
        remitente_id = request.form.get('remitente_id')
        destinatario_id = request.form.get('destinatario_id')
        asunto = request.form.get('asunto')
        contenido = request.form.get('contenido')
        
        if not all([remitente_id, destinatario_id, asunto, contenido]):
            flash('Todos los campos son obligatorios', 'error')
            return redirect(url_for('nuevo_mensaje'))
        
        # Verificar permisos
        user = Usuario.query.get(session['user_id'])
        remitente = Personaje.query.get(remitente_id)
        if not user.es_admin and remitente.creador_id != user.id:
            flash('No tienes permisos para enviar mensajes con este personaje', 'error')
            return redirect(url_for('nuevo_mensaje'))
        
        # Crear el mensaje
        mensaje = Mensaje(
            remitente_id=remitente_id,
            destinatario_id=destinatario_id,
            asunto=asunto,
            contenido=contenido
        )
        
        db.session.add(mensaje)
        db.session.commit()
        
        flash('Mensaje enviado exitosamente', 'success')
        return redirect(url_for('ver_mensajes', personaje_id=remitente_id))
    
    # GET: mostrar formulario
    user = Usuario.query.get(session['user_id'])
    personajes = Personaje.query.filter_by(creador_id=user.id).all() if not user.es_admin else Personaje.query.all()
    todos_personajes = Personaje.query.all()
    
    return render_template('nuevo_mensaje.html', personajes=personajes, todos_personajes=todos_personajes)

@app.route('/mensaje/<int:mensaje_id>/leer')
@login_required
def leer_mensaje(mensaje_id):
    """Marcar mensaje como leído y mostrarlo"""
    mensaje = Mensaje.query.get_or_404(mensaje_id)
    
    # Verificar permisos
    user = Usuario.query.get(session['user_id'])
    if not user.es_admin and mensaje.destinatario.creador_id != user.id:
        flash('No tienes permisos para leer este mensaje', 'error')
        return redirect(url_for('mensajes'))
    
    # Marcar como leído
    if not mensaje.leido:
        mensaje.leido = True
        db.session.commit()
    
    return render_template('leer_mensaje.html', mensaje=mensaje)

@app.route('/mensaje/<int:mensaje_id>/eliminar', methods=['POST'])
@login_required
def eliminar_mensaje(mensaje_id):
    """Eliminar un mensaje"""
    mensaje = Mensaje.query.get_or_404(mensaje_id)
    
    # Verificar permisos (solo el destinatario puede eliminar)
    user = Usuario.query.get(session['user_id'])
    if not user.es_admin and mensaje.destinatario.creador_id != user.id:
        flash('No tienes permisos para eliminar este mensaje', 'error')
        return redirect(url_for('mensajes'))
    
    personaje_id = mensaje.destinatario_id
    db.session.delete(mensaje)
    db.session.commit()
    
    flash('Mensaje eliminado exitosamente', 'success')
    return redirect(url_for('ver_mensajes', personaje_id=personaje_id))

@app.route('/admin/usuarios')
@admin_required
def admin_usuarios():
    """Listar todos los usuarios para administración"""
    usuarios = Usuario.query.order_by(Usuario.username).all()
    
    # Contar personajes por usuario
    for usuario in usuarios:
        usuario.num_personajes = Personaje.query.filter_by(creador_id=usuario.id).count()
        usuario.limite_actual = usuario.obtener_limite_personajes()
    
    return render_template('admin_usuarios.html', usuarios=usuarios)

@app.route('/admin/usuario/<int:usuario_id>/cambiar-nivel', methods=['POST'])
@admin_required
def cambiar_nivel_usuario(usuario_id):
    """Cambiar el nivel de un usuario"""
    usuario = Usuario.query.get_or_404(usuario_id)
    nuevo_nivel = request.form.get('nivel')
    
    niveles_validos = ['normal', 'premium', 'vip', 'legendario']
    if nuevo_nivel not in niveles_validos:
        flash('Nivel no válido', 'error')
        return redirect(url_for('admin_usuarios'))
    
    usuario.nivel_usuario = nuevo_nivel
    db.session.commit()
    
    flash(f'Nivel de {usuario.username} cambiado a {nuevo_nivel}', 'success')
    return redirect(url_for('admin_usuarios'))

@app.route('/admin/regalar-rastamonios')
@admin_required
def admin_regalar_rastamonios():
    """Página para regalar rastamonios a personajes"""
    personajes = Personaje.query.order_by(Personaje.nombre).all()
    
    # Agrupar personajes por usuario
    usuarios = {}
    for personaje in personajes:
        if personaje.creador_id not in usuarios:
            usuarios[personaje.creador_id] = {
                'personajes': [],
                'total_rastamonios': 0
            }
        usuarios[personaje.creador_id]['personajes'].append(personaje)
        usuarios[personaje.creador_id]['total_rastamonios'] += personaje.rastamonios
    
    return render_template('admin_regalar_rastamonios.html', 
                         personajes=personajes, 
                         usuarios=usuarios)

@app.route('/admin/personaje/<int:personaje_id>/regalar-rastamonios', methods=['POST'])
@admin_required
def regalar_rastamonios_personaje(personaje_id):
    """Regalar rastamonios a un personaje específico"""
    personaje = Personaje.query.get_or_404(personaje_id)
    cantidad = request.form.get('cantidad')
    motivo = request.form.get('motivo', 'Regalo del administrador')
    
    try:
        cantidad = int(cantidad)
        if cantidad <= 0:
            flash('La cantidad debe ser mayor a 0', 'error')
            return redirect(url_for('admin_regalar_rastamonios'))
    except ValueError:
        flash('Cantidad no válida', 'error')
        return redirect(url_for('admin_regalar_rastamonios'))
    
    # Regalar los rastamonios
    personaje.rastamonios += cantidad
    db.session.commit()
    
    flash(f'Se regalaron {cantidad} rastamonios a {personaje.nombre}. Motivo: {motivo}', 'success')
    return redirect(url_for('admin_regalar_rastamonios'))

@app.route('/admin/usuario/<int:usuario_id>/regalar-rastamonios-todos', methods=['POST'])
@admin_required
def regalar_rastamonios_todos_personajes(usuario_id):
    """Regalar rastamonios a todos los personajes de un usuario"""
    usuario = Usuario.query.get_or_404(usuario_id)
    cantidad = request.form.get('cantidad')
    motivo = request.form.get('motivo', 'Regalo del administrador')
    
    try:
        cantidad = int(cantidad)
        if cantidad <= 0:
            flash('La cantidad debe ser mayor a 0', 'error')
            return redirect(url_for('admin_regalar_rastamonios'))
    except ValueError:
        flash('Cantidad no válida', 'error')
        return redirect(url_for('admin_regalar_rastamonios'))
    
    # Regalar a todos los personajes del usuario
    personajes = Personaje.query.filter_by(creador_id=usuario_id).all()
    for personaje in personajes:
        personaje.rastamonios += cantidad
    
    db.session.commit()
    
    flash(f'Se regalaron {cantidad} rastamonios a todos los personajes de {usuario.username} ({len(personajes)} personajes). Motivo: {motivo}', 'success')
    return redirect(url_for('admin_regalar_rastamonios'))

@app.route('/comprar-slot-personaje', methods=['GET', 'POST'])
@login_required
def comprar_slot_personaje():
    """Comprar un slot adicional de personaje"""
    user = Usuario.query.get(session['user_id'])
    
    if request.method == 'POST':
        # Verificar que el usuario tiene suficientes rastamonios
        precio = user.obtener_precio_siguiente_slot()
        
        # Obtener todos los personajes del usuario
        personajes = Personaje.query.filter_by(creador_id=user.id).all()
        if not personajes:
            flash('Necesitas al menos un personaje para comprar slots adicionales', 'error')
            return redirect(url_for('index'))
        
        # Calcular el total de rastamonios de todos los personajes
        total_rastamonios = sum(p.rastamonios for p in personajes)
        
        if total_rastamonios < precio:
            flash(f'No tienes suficientes rastamonios. Necesitas {precio} rastamonios. Total disponible: {total_rastamonios} rastamonios.', 'error')
            return redirect(url_for('comprar_slot_personaje'))
        
        # Distribuir el costo entre los personajes (priorizando los que tienen más)
        rastamonios_restantes = precio
        personajes_ordenados = sorted(personajes, key=lambda p: p.rastamonios, reverse=True)
        
        for personaje in personajes_ordenados:
            if rastamonios_restantes <= 0:
                break
            
            if personaje.rastamonios >= rastamonios_restantes:
                personaje.rastamonios -= rastamonios_restantes
                rastamonios_restantes = 0
            else:
                rastamonios_restantes -= personaje.rastamonios
                personaje.rastamonios = 0
        
        user.slots_comprados += 1
        db.session.commit()
        
        flash(f'¡Slot de personaje comprado exitosamente! Ahora puedes crear hasta {user.obtener_limite_personajes()} personajes.', 'success')
        return redirect(url_for('index'))
    
    # GET: mostrar información de compra
    precio = user.obtener_precio_siguiente_slot()
    personajes = Personaje.query.filter_by(creador_id=user.id).all()
    total_rastamonios = sum(p.rastamonios for p in personajes) if personajes else 0
    
    return render_template('comprar_slot_personaje.html', 
                         user=user, 
                         precio=precio, 
                         personajes=personajes,
                         total_rastamonios=total_rastamonios)

@app.cli.command('asignar_rastamonios')
def asignar_rastamonios():
    from models import Personaje, db
    personajes = Personaje.query.all()
    for p in personajes:
        p.rastamonios = 10000
    db.session.commit()
    print(f'Se asignaron 10000 rastamonios a {len(personajes)} personajes.')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 