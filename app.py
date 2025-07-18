import json
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, abort
import os
from werkzeug.utils import secure_filename
from datetime import datetime
from functools import wraps
from models import db, Personaje, Arma, ArmaNueva, InvocacionNueva, Planeta, Elemento, Usuario, Ranking, SolicitudElemento, SolicitudArma, SolicitudArmaNueva, SolicitudInvocacionNueva, TiendaItem, Compra, Mensaje, Mision, MisionPersonaje, SolicitudPlaneta, Ataque, AtaquePersonaje, Clan, SolicitudClan, MiembroClan
from sqlalchemy.orm import joinedload, selectinload

app = Flask(__name__)
app.secret_key = 'expediente_digital_secret_key'

# Configuración para subida de archivos
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Configuración de la base de datos
instance_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance')
if not os.path.exists(instance_dir):
    os.makedirs(instance_dir)
db_path = os.path.join(instance_dir, 'expedientes.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
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
    """Página principal con lista de personajes del usuario"""
    # Contadores globales
    total_personajes = Personaje.query.count()
    total_armas = ArmaNueva.query.count()
    total_invocaciones = InvocacionNueva.query.count()
    # Contar personajes S según el nivel calculado
    personajes_all = Personaje.query.options(selectinload(Personaje.armas_nuevas), selectinload(Personaje.invocaciones_nuevas)).all()
    total_nivel_s = sum(1 for p in personajes_all if p.nivel_auto == 'S')
    # Contadores por nivel calculado
    total_nivel_d = sum(1 for p in personajes_all if p.nivel_auto == 'D')
    total_nivel_c = sum(1 for p in personajes_all if p.nivel_auto == 'C')
    total_nivel_b = sum(1 for p in personajes_all if p.nivel_auto == 'B')
    total_nivel_a = sum(1 for p in personajes_all if p.nivel_auto == 'A')

    if 'user_id' in session:
        # Obtener personaje activo si existe
        personaje_activo = None
        if 'personaje_activo_id' in session:
            personaje_activo = Personaje.query.get(session['personaje_activo_id'])
            # Verificar que el personaje activo pertenece al usuario
            if not personaje_activo or personaje_activo.creador_id != session['user_id']:
                personaje_activo = None
                session.pop('personaje_activo_id', None)
        
        # Si hay personaje activo, mostrar solo ese personaje
        if personaje_activo:
            personajes = [personaje_activo]
            mostrar_todos = False
        else:
            # Mostrar todos los personajes del usuario
            personajes = Personaje.query.options(selectinload(Personaje.armas_nuevas), selectinload(Personaje.invocaciones_nuevas)).filter_by(creador_id=session['user_id']).all()
            mostrar_todos = True
        
        return render_template('index.html', personajes=personajes, es_mis_personajes=True,
                               total_personajes=total_personajes, total_armas=total_armas,
                               total_invocaciones=total_invocaciones, total_nivel_s=total_nivel_s,
                               total_nivel_d=total_nivel_d, total_nivel_c=total_nivel_c, total_nivel_b=total_nivel_b, total_nivel_a=total_nivel_a,
                               personaje_activo=personaje_activo, mostrar_todos=mostrar_todos)
    else:
        # Mostrar solo los 3 primeros del ranking para usuarios no logueados
        if Ranking.query.count() == 0:
            actualizar_rankings()
        
        top_rankings = Ranking.query.order_by(Ranking.posicion).limit(3).all()
        personajes = [ranking.personaje for ranking in top_rankings]
        return render_template('index.html', personajes=personajes, es_mis_personajes=False,
                               total_personajes=total_personajes, total_armas=total_armas,
                               total_invocaciones=total_invocaciones, total_nivel_s=total_nivel_s,
                               total_nivel_d=total_nivel_d, total_nivel_c=total_nivel_c, total_nivel_b=total_nivel_b, total_nivel_a=total_nivel_a)

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
        edad = request.form.get('edad')
        descripcion = request.form.get('descripcion')
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
            dimension=None,  # Sin dimensión inicial
            planeta=None,    # Sin planeta inicial
            edad=int(edad) if edad else 0,
            descripcion=descripcion,
            nivel='D',  # Asignar nivel D por defecto
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
    
    # Obtener solicitudes pendientes de planeta para este personaje
    solicitudes_pendientes = []
    if 'user_id' in session and (session.get('es_admin') or personaje.creador_id == session['user_id']):
        from models import SolicitudPlaneta
        solicitudes_pendientes = SolicitudPlaneta.query.filter_by(
            personaje_id=personaje.id, 
            estado='pendiente'
        ).all()
    
    return render_template('ver_personaje.html', personaje=personaje, solicitudes_pendientes=solicitudes_pendientes)

@app.route('/personaje/<int:personaje_id>/seleccionar', methods=['POST'])
@login_required
def seleccionar_personaje_activo(personaje_id):
    """Seleccionar un personaje como activo"""
    personaje = Personaje.query.get_or_404(personaje_id)
    
    # Verificar que el personaje pertenece al usuario
    if personaje.creador_id != session['user_id']:
        flash('Solo puedes seleccionar tus propios personajes como activos', 'error')
        return redirect(url_for('index'))
    
    session['personaje_activo_id'] = personaje_id
    flash(f'Has seleccionado a {personaje.nombre} como tu personaje activo', 'success')
    return redirect(url_for('index'))

@app.route('/personaje/desactivar', methods=['POST'])
@login_required
def desactivar_personaje_activo():
    """Desactivar el personaje activo y mostrar todos los personajes"""
    if 'personaje_activo_id' in session:
        session.pop('personaje_activo_id', None)
        flash('Has desactivado el personaje activo. Ahora se muestran todos tus personajes', 'info')
    return redirect(url_for('index'))

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

@app.route('/personaje/<int:personaje_id>/asignar-planeta', methods=['GET', 'POST'])
@can_edit_personaje
def asignar_planeta_personaje(personaje_id):
    """Asignar dimensión y planeta a un personaje"""
    personaje = Personaje.query.get_or_404(personaje_id)
    if request.method == 'POST':
        dimension = request.form.get('dimension')
        planeta_nombre = request.form.get('planeta')
        planeta_obj = Planeta.query.filter_by(nombre=planeta_nombre).first() if planeta_nombre and planeta_nombre != 'sin_planeta' else None

        # Si no se selecciona dimensión, quitar asignación
        if not dimension:
            personaje.dimension = None
            personaje.planeta = None
            db.session.commit()
            flash('Dimensión y planeta removidos del personaje', 'success')
            return redirect(url_for('ver_personaje', personaje_id=personaje_id))

        # Asignar dimensión
        personaje.dimension = dimension

        # Si se selecciona planeta
        if planeta_obj:
            if planeta_obj.es_publico:
                personaje.planeta = planeta_obj.nombre
                db.session.commit()
                flash('Dimensión y planeta asignados exitosamente', 'success')
                return redirect(url_for('ver_personaje', personaje_id=personaje_id))
            else:
                # Verificar si el usuario es dueño del planeta
                user = Usuario.query.get(session['user_id'])
                if user.es_admin or planeta_obj.duenio_id == user.id:
                    # El usuario es admin o dueño del planeta, asignar directamente
                    personaje.planeta = planeta_obj.nombre
                    db.session.commit()
                    flash('Dimensión y planeta asignados exitosamente', 'success')
                    return redirect(url_for('ver_personaje', personaje_id=personaje_id))
                else:
                    # Planeta restringido y no es dueño: crear solicitud si no existe
                    solicitud_existente = SolicitudPlaneta.query.filter_by(personaje_id=personaje.id, planeta_id=planeta_obj.id, estado='pendiente').first()
                    if solicitud_existente:
                        flash('Ya tienes una solicitud pendiente para este planeta. Espera la respuesta del dueño.', 'info')
                    else:
                        nueva_solicitud = SolicitudPlaneta(personaje_id=personaje.id, planeta_id=planeta_obj.id)
                        db.session.add(nueva_solicitud)
                        db.session.commit()
                        flash('Solicitud enviada al dueño del planeta. Quedas en espera de respuesta.', 'info')
                    return redirect(url_for('ver_personaje', personaje_id=personaje_id))
        else:
            personaje.planeta = None
            db.session.commit()
            flash('Dimensión asignada, sin planeta.', 'success')
            return redirect(url_for('ver_personaje', personaje_id=personaje_id))

    # GET: mostrar formulario de asignación
    dimensiones = ['Universo', 'Cielo', 'Infierno', 'Limbo']
    planetas = Planeta.query.all()
    return render_template('asignar_planeta_personaje.html', 
                         personaje=personaje, 
                         dimensiones=dimensiones, 
                         planetas=planetas)

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
    invocacion = InvocacionNueva.query.filter_by(id=invocacion_id, personaje_id=personaje_id).first_or_404()
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
@login_required
def nuevo_planeta():
    """Crear un nuevo planeta"""
    usuarios = Usuario.query.order_by(Usuario.username).all()
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        dimension = request.form.get('dimension')
        descripcion = request.form.get('descripcion')
        es_publico = request.form.get('es_publico') == '1'
        duenio_id = int(request.form.get('duenio_id')) if request.form.get('duenio_id') else session['user_id']

        # Verificar si el planeta ya existe
        planeta_existente = Planeta.query.filter_by(nombre=nombre).first()
        if planeta_existente:
            flash('Ya existe un planeta con ese nombre', 'error')
            return redirect(request.url)

        nuevo_planeta = Planeta(
            nombre=nombre,
            dimension=dimension,
            descripcion=descripcion,
            es_publico=es_publico,
            duenio_id=duenio_id
        )

        db.session.add(nuevo_planeta)
        db.session.commit()

        flash('Planeta creado exitosamente', 'success')
        return redirect(url_for('listar_planetas'))

    return render_template('nuevo_planeta.html', usuarios=usuarios)

@app.route('/planeta/<int:planeta_id>/editar', methods=['GET', 'POST'])
@admin_required
def editar_planeta(planeta_id):
    """Editar un planeta existente"""
    planeta = Planeta.query.get_or_404(planeta_id)
    usuarios = Usuario.query.order_by(Usuario.username).all()
    puede_cambiar_duenio = session.get('es_admin') or session.get('user_id') == (planeta.duenio_id or 0)

    if request.method == 'POST':
        nombre = request.form.get('nombre')
        dimension = request.form.get('dimension')
        descripcion = request.form.get('descripcion')
        es_publico = request.form.get('es_publico') == '1'
        if puede_cambiar_duenio:
            duenio_id = int(request.form.get('duenio_id')) if request.form.get('duenio_id') else planeta.duenio_id
            planeta.duenio_id = duenio_id
        planeta.nombre = nombre
        planeta.dimension = dimension
        planeta.descripcion = descripcion
        planeta.es_publico = es_publico

        db.session.commit()
        flash('Planeta actualizado exitosamente', 'success')
        return redirect(url_for('listar_planetas'))

    planeta.num_personajes = Personaje.query.filter_by(planeta=planeta.nombre).count()
    personajes_planeta = Personaje.query.filter_by(planeta=planeta.nombre).all()

    return render_template('editar_planeta.html', planeta=planeta, personajes_planeta=personajes_planeta, usuarios=usuarios, puede_cambiar_duenio=puede_cambiar_duenio)

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

@app.route('/planeta/<int:planeta_id>')
def ver_planeta(planeta_id):
    """Ver detalles de un planeta específico y sus personajes"""
    planeta = Planeta.query.get_or_404(planeta_id)
    personajes_planeta = Personaje.query.filter_by(planeta=planeta.nombre).all()
    solicitudes_pendientes = []
    puede_gestionar = False
    if 'user_id' in session:
        puede_gestionar = session.get('es_admin') or session['user_id'] == (planeta.duenio_id or 0)
        if puede_gestionar:
            from models import SolicitudPlaneta
            solicitudes_pendientes = SolicitudPlaneta.query.filter_by(planeta_id=planeta.id, estado='pendiente').all()
    return render_template('ver_planeta.html', planeta=planeta, personajes_planeta=personajes_planeta, solicitudes_pendientes=solicitudes_pendientes, puede_gestionar=puede_gestionar)

@app.route('/solicitud-planeta/<int:solicitud_id>/aceptar', methods=['POST'])
def aceptar_solicitud_planeta(solicitud_id):
    from models import SolicitudPlaneta
    solicitud = SolicitudPlaneta.query.get_or_404(solicitud_id)
    planeta = Planeta.query.get(solicitud.planeta_id)
    if not (session.get('es_admin') or session['user_id'] == (planeta.duenio_id or 0)):
        abort(403)
    solicitud.estado = 'aceptada'
    solicitud.fecha_respuesta = datetime.utcnow()
    personaje = Personaje.query.get(solicitud.personaje_id)
    personaje.planeta = planeta.nombre
    personaje.dimension = planeta.dimension
    db.session.commit()
    flash('Solicitud aceptada. El personaje ha sido asignado al planeta.', 'success')
    return redirect(url_for('ver_planeta', planeta_id=planeta.id))

@app.route('/solicitud-planeta/<int:solicitud_id>/rechazar', methods=['POST'])
def rechazar_solicitud_planeta(solicitud_id):
    from models import SolicitudPlaneta
    solicitud = SolicitudPlaneta.query.get_or_404(solicitud_id)
    planeta = Planeta.query.get(solicitud.planeta_id)
    if not (session.get('es_admin') or session['user_id'] == (planeta.duenio_id or 0)):
        abort(403)
    solicitud.estado = 'rechazada'
    solicitud.fecha_respuesta = datetime.utcnow()
    db.session.commit()
    flash('Solicitud rechazada.', 'info')
    return redirect(url_for('ver_planeta', planeta_id=planeta.id))

@app.route('/solicitud-planeta/<int:solicitud_id>/cancelar', methods=['POST'])
def cancelar_solicitud_planeta(solicitud_id):
    from models import SolicitudPlaneta
    solicitud = SolicitudPlaneta.query.get_or_404(solicitud_id)
    if session['user_id'] != Personaje.query.get(solicitud.personaje_id).creador_id:
        abort(403)
    solicitud.estado = 'cancelada'
    solicitud.fecha_respuesta = datetime.utcnow()
    db.session.commit()
    flash('Solicitud cancelada.', 'info')
    return redirect(url_for('ver_personaje', personaje_id=solicitud.personaje_id))

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

@app.route('/explorar-personajes')
def explorar_personajes():
    """Página para explorar todos los personajes con filtros"""
    # Obtener parámetros de filtro
    dimension = request.args.get('dimension', '')
    planeta = request.args.get('planeta', '')
    busqueda = request.args.get('busqueda', '')
    
    # Construir consulta base
    query = Personaje.query
    
    # Aplicar filtros
    if dimension:
        query = query.filter(Personaje.dimension == dimension)
    
    if planeta and dimension == 'Universo':
        query = query.filter(Personaje.planeta == planeta)
    
    if busqueda:
        query = query.filter(Personaje.nombre.ilike(f'%{busqueda}%'))
    
    # Obtener personajes filtrados
    personajes = query.order_by(Personaje.nombre).all()
    
    # Obtener dimensiones únicas para el filtro
    dimensiones = db.session.query(Personaje.dimension).distinct().all()
    dimensiones = [d[0] for d in dimensiones]
    
    # Obtener planetas únicos para el filtro (solo si se selecciona Universo)
    planetas = []
    if dimension == 'Universo':
        planetas = db.session.query(Personaje.planeta).filter(
            Personaje.dimension == 'Universo',
            Personaje.planeta.isnot(None)
        ).distinct().all()
        planetas = [p[0] for p in planetas if p[0]]
    
    return render_template('explorar_personajes.html', 
                         personajes=personajes, 
                         dimensiones=dimensiones,
                         planetas=planetas,
                         filtro_dimension=dimension,
                         filtro_planeta=planeta,
                         busqueda=busqueda)

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
        solicitudes = SolicitudArmaNueva.query.order_by(SolicitudArmaNueva.fecha_solicitud.desc()).all()
    else:
        # Usuarios normales ven solo sus solicitudes
        solicitudes = SolicitudArmaNueva.query.filter_by(usuario_id=user.id).order_by(SolicitudArmaNueva.fecha_solicitud.desc()).all()
    
    return render_template('solicitudes_armas.html', solicitudes=solicitudes)

@app.route('/solicitud-arma/nueva', methods=['GET', 'POST'])
@login_required
def nueva_solicitud_arma():
    """Crear nueva solicitud de arma"""
    if request.method == 'POST':
        personaje_id = request.form.get('personaje_id')
        nombre = request.form.get('nombre')
        descripcion = request.form.get('descripcion')
        poder = int(request.form.get('poder', 0))
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
        
        nueva_solicitud = SolicitudArmaNueva(
            usuario_id=user.id,
            personaje_id=personaje_id,
            nombre=nombre,
            descripcion=descripcion,
            imagen=imagen,
            poder=poder,
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
    solicitud = SolicitudArmaNueva.query.get_or_404(solicitud_id)
    respuesta = request.form.get('respuesta', 'Solicitud aprobada')
    poder_final = int(request.form.get('poder', solicitud.poder))
    
    solicitud.estado = 'aprobada'
    solicitud.respuesta_admin = respuesta
    solicitud.fecha_respuesta = datetime.utcnow()
    
    # Crear la arma y agregarla al personaje
    nueva_arma = ArmaNueva(
        nombre=solicitud.nombre,
        descripcion=solicitud.descripcion,
        imagen=solicitud.imagen,
        poder=poder_final,
        personaje_id=solicitud.personaje_id
    )
    
    db.session.add(nueva_arma)
    
    # Actualizar rankings
    actualizar_rankings()
    
    db.session.commit()
    flash(f'Solicitud de arma aprobada exitosamente con {poder_final} de poder', 'success')
    return redirect(url_for('listar_solicitudes_armas'))

@app.route('/solicitud-arma/<int:solicitud_id>/rechazar', methods=['POST'])
@admin_required
def rechazar_solicitud_arma(solicitud_id):
    """Rechazar una solicitud de arma"""
    solicitud = SolicitudArmaNueva.query.get_or_404(solicitud_id)
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
        solicitudes = SolicitudInvocacionNueva.query.order_by(SolicitudInvocacionNueva.fecha_solicitud.desc()).all()
    else:
        # Usuarios normales ven solo sus solicitudes
        solicitudes = SolicitudInvocacionNueva.query.filter_by(usuario_id=user.id).order_by(SolicitudInvocacionNueva.fecha_solicitud.desc()).all()
    
    return render_template('solicitudes_invocaciones.html', solicitudes=solicitudes)

@app.route('/solicitud-invocacion/nueva', methods=['GET', 'POST'])
@login_required
def nueva_solicitud_invocacion():
    """Crear nueva solicitud de invocación"""
    if request.method == 'POST':
        personaje_id = request.form.get('personaje_id')
        nombre = request.form.get('nombre')
        descripcion = request.form.get('descripcion')
        poder = int(request.form.get('poder', 0))
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
        
        nueva_solicitud = SolicitudInvocacionNueva(
            usuario_id=user.id,
            personaje_id=personaje_id,
            nombre=nombre,
            descripcion=descripcion,
            imagen=imagen,
            poder=poder,
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
    solicitud = SolicitudInvocacionNueva.query.get_or_404(solicitud_id)
    respuesta = request.form.get('respuesta', 'Solicitud aprobada')
    poder_final = int(request.form.get('poder', solicitud.poder))
    
    solicitud.estado = 'aprobada'
    solicitud.respuesta_admin = respuesta
    solicitud.fecha_respuesta = datetime.utcnow()
    
    # Crear la invocación y agregarla al personaje
    nueva_invocacion = InvocacionNueva(
        nombre=solicitud.nombre,
        descripcion=solicitud.descripcion,
        imagen=solicitud.imagen,
        poder=poder_final,
        personaje_id=solicitud.personaje_id
    )
    
    db.session.add(nueva_invocacion)
    
    # Actualizar rankings
    actualizar_rankings()
    
    db.session.commit()
    flash(f'Solicitud de invocación aprobada exitosamente con {poder_final} de poder', 'success')
    return redirect(url_for('listar_solicitudes_invocaciones'))

@app.route('/solicitud-invocacion/<int:solicitud_id>/rechazar', methods=['POST'])
@admin_required
def rechazar_solicitud_invocacion(solicitud_id):
    """Rechazar una solicitud de invocación"""
    solicitud = SolicitudInvocacionNueva.query.get_or_404(solicitud_id)
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
    # Ítems normales disponibles
    items_normales = TiendaItem.query.filter_by(disponible=True, es_unico=False).all()
    
    # Obtener todos los ítems únicos
    items_unicos = TiendaItem.query.filter_by(disponible=True, es_unico=True).all()
    
    # Obtener compras de ítems únicos en venta
    compras_unicos_en_venta = Compra.query.filter_by(en_venta=True).all()
    items_unicos_en_venta_ids = [c.item_id for c in compras_unicos_en_venta if c.item and c.item.es_unico and c.item.disponible]
    
    # Filtrar ítems únicos: solo mostrar los que están en venta o nunca han sido comprados
    items_unicos_disponibles = []
    for item in items_unicos:
        # Si el ítem está en venta, incluirlo
        if item.id in items_unicos_en_venta_ids:
            items_unicos_disponibles.append(item)
        # Si el ítem nunca ha sido comprado, incluirlo
        elif Compra.query.filter_by(item_id=item.id).count() == 0:
            items_unicos_disponibles.append(item)
    
    # Unir todos los ítems a mostrar
    items = items_normales + items_unicos_disponibles
    
    user = Usuario.query.get(session['user_id'])
    
    # Obtener personaje activo si existe
    personaje_activo = None
    if 'personaje_activo_id' in session:
        personaje_activo = Personaje.query.get(session['personaje_activo_id'])
        # Verificar que el personaje activo pertenece al usuario
        if not personaje_activo or personaje_activo.creador_id != session['user_id']:
            personaje_activo = None
            session.pop('personaje_activo_id', None)
    
    # Si hay personaje activo, mostrar solo ese personaje
    if personaje_activo:
        personajes = [personaje_activo]
        mostrar_todos = False
    else:
        # Mostrar todos los personajes del usuario
        personajes = Personaje.query.filter_by(creador_id=user.id).all() if not user.es_admin else Personaje.query.all()
        mostrar_todos = True
    
    return render_template('tienda.html', items=items, personajes=personajes, personaje_activo=personaje_activo, mostrar_todos=mostrar_todos)

@app.route('/personaje/<int:personaje_id>/tienda')
@login_required
def tienda_personaje(personaje_id):
    """Tienda específica para un personaje"""
    personaje = Personaje.query.get_or_404(personaje_id)
    
    # Verificar que el personaje pertenece al usuario
    user = Usuario.query.get(session['user_id'])
    if personaje.creador_id != user.id:
        flash('No puedes acceder a la tienda con personajes que no son tuyos', 'error')
        return redirect(url_for('index'))
    
    # Ítems normales disponibles
    items_normales = TiendaItem.query.filter_by(disponible=True, es_unico=False).all()
    
    # Obtener todos los ítems únicos
    items_unicos = TiendaItem.query.filter_by(disponible=True, es_unico=True).all()
    
    # Obtener compras de ítems únicos en venta
    compras_unicos_en_venta = Compra.query.filter_by(en_venta=True).all()
    items_unicos_en_venta_ids = [c.item_id for c in compras_unicos_en_venta if c.item and c.item.es_unico and c.item.disponible]
    
    # Filtrar ítems únicos: solo mostrar los que están en venta o nunca han sido comprados
    items_unicos_disponibles = []
    for item in items_unicos:
        # Si el ítem está en venta, incluirlo
        if item.id in items_unicos_en_venta_ids:
            items_unicos_disponibles.append(item)
        # Si el ítem nunca ha sido comprado, incluirlo
        elif Compra.query.filter_by(item_id=item.id).count() == 0:
            items_unicos_disponibles.append(item)
    
    # Unir todos los ítems a mostrar
    items = items_normales + items_unicos_disponibles
    
    return render_template('tienda_personaje.html', items=items, personaje=personaje, user=user)

@app.route('/personaje/<int:personaje_id>/tienda/item/<int:item_id>')
@login_required
def ver_item_tienda_personaje(personaje_id, item_id):
    """Ver detalle de un ítem específico para un personaje"""
    personaje = Personaje.query.get_or_404(personaje_id)
    
    # Verificar que el personaje pertenece al usuario
    user = Usuario.query.get(session['user_id'])
    if personaje.creador_id != user.id:
        flash('No puedes acceder a la tienda con personajes que no son tuyos', 'error')
        return redirect(url_for('index'))
    
    item = TiendaItem.query.get_or_404(item_id)
    
    # Verificar si el ítem está disponible
    if not item.disponible:
        flash('Este ítem no está disponible', 'error')
        return redirect(url_for('tienda_personaje', personaje_id=personaje_id))
    
    # Verificar si ya fue comprado por este personaje
    ya_comprado = Compra.query.filter_by(item_id=item.id, personaje_id=personaje.id).first()
    
    # Para ítems únicos, verificar si están en venta
    compra_en_venta = None
    if item.es_unico:
        compra_en_venta = Compra.query.filter_by(item_id=item.id, en_venta=True).first()
    
    return render_template('ver_item_tienda_personaje.html', 
                         item=item, 
                         personaje=personaje, 
                         ya_comprado=ya_comprado,
                         compra_en_venta=compra_en_venta,
                         user=user)

@app.route('/tienda/comprar', methods=['POST'])
@login_required
def comprar_item():
    personaje_id = request.form.get('personaje_id')
    item_id = request.form.get('item_id')
    cantidad = int(request.form.get('cantidad', 1))
    personaje = Personaje.query.get_or_404(personaje_id)
    item = TiendaItem.query.get_or_404(item_id)
    
    # Verificar si el personaje ya tiene este item
    compra_existente = Compra.query.filter_by(personaje_id=personaje.id, item_id=item.id).first()
    if compra_existente:
        flash('Este personaje ya ha comprado este ítem. Solo puedes comprarlo una vez.', 'error')
        return redirect(url_for('tienda'))
    
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
        if compra.item.es_unico:
            # Ítem único: poner en venta, guardar precio y vendedor, no acreditar rastamonios
            compra.en_venta = True
            compra.precio_venta = precio_venta
            compra.vendedor_id = personaje.id
            compra.item.disponible = True
            db.session.commit()
            flash(f'Has puesto {compra.item.nombre} en venta por {precio_venta} rastamonios. Recibirás el pago solo si otro usuario lo compra.', 'success')
            return redirect(url_for('ver_personaje', personaje_id=personaje_id))
        else:
            # Ítem infinito: solo se puede vender por el 75% del valor de compra
            precio_real = int(compra.item.precio * 0.75)
            if precio_venta != precio_real:
                flash(f'El precio de venta para este ítem debe ser exactamente el 75% del valor de compra: {precio_real} rastamonios.', 'error')
                return redirect(url_for('vender_item', personaje_id=personaje_id, compra_id=compra_id))
            personaje.rastamonios += precio_real
            if compra.item.stock >= 0:
                compra.item.stock += compra.cantidad
                if not compra.item.disponible and compra.item.stock > 0:
                    compra.item.disponible = True
            db.session.delete(compra)
            db.session.commit()
            flash(f'Has vendido {compra.item.nombre} por {precio_real} rastamonios', 'success')
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

@app.route('/admin/usuario/<int:usuario_id>/eliminar', methods=['POST'])
@admin_required
def eliminar_usuario(usuario_id):
    """Eliminar un usuario por infracciones"""
    usuario = Usuario.query.get_or_404(usuario_id)
    motivo = request.form.get('motivo', 'Infracción de normas')
    
    # Verificar que no se elimine a sí mismo
    if usuario.id == session.get('user_id'):
        flash('No puedes eliminar tu propia cuenta', 'error')
        return redirect(url_for('admin_usuarios'))
    
    # Verificar que no se elimine a otro admin
    if usuario.es_admin:
        flash('No se pueden eliminar cuentas de administrador', 'error')
        return redirect(url_for('admin_usuarios'))
    
    # Eliminar todos los personajes del usuario
    personajes = Personaje.query.filter_by(creador_id=usuario_id).all()
    for personaje in personajes:
        # Eliminar misiones en progreso
        MisionPersonaje.query.filter_by(personaje_id=personaje.id).delete()
        # Eliminar compras
        Compra.query.filter_by(personaje_id=personaje.id).delete()
        # Eliminar armas e invocaciones
        Arma.query.filter_by(personaje_id=personaje.id).delete()
        InvocacionNueva.query.filter_by(personaje_id=personaje.id).delete()
        # Eliminar mensajes
        Mensaje.query.filter_by(remitente_id=personaje.id).delete()
        Mensaje.query.filter_by(destinatario_id=personaje.id).delete()
        # Eliminar solicitudes
        Solicitud.query.filter_by(personaje_id=personaje.id).delete()
        SolicitudArma.query.filter_by(personaje_id=personaje.id).delete()
        SolicitudInvocacionNueva.query.filter_by(personaje_id=personaje.id).delete()
        # Eliminar el personaje
        db.session.delete(personaje)
    
    # Eliminar el usuario
    db.session.delete(usuario)
    db.session.commit()
    
    flash(f'Usuario {usuario.username} eliminado por: {motivo}', 'success')
    return redirect(url_for('admin_usuarios'))

@app.route('/admin/usuario/<int:usuario_id>/toggle-admin', methods=['POST'])
@admin_required
def toggle_admin_usuario(usuario_id):
    """Dar o quitar permisos de administrador a un usuario"""
    usuario = Usuario.query.get_or_404(usuario_id)
    accion = request.form.get('accion')
    
    # Verificar que no se modifique a sí mismo
    if usuario.id == session.get('user_id'):
        flash('No puedes modificar tu propio estado de administrador', 'error')
        return redirect(url_for('admin_usuarios'))
    
    if accion == 'dar_admin':
        usuario.es_admin = True
        flash(f'Se otorgaron permisos de administrador a {usuario.username}', 'success')
    elif accion == 'quitar_admin':
        usuario.es_admin = False
        flash(f'Se revocaron los permisos de administrador de {usuario.username}', 'success')
    else:
        flash('Acción no válida', 'error')
        return redirect(url_for('admin_usuarios'))
    
    db.session.commit()
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

# ===== ADMINISTRACIÓN DE PODER REGALADO =====

@app.route('/admin/regalar-poder')
@admin_required
def admin_regalar_poder():
    """Panel para regalar poder a personajes"""
    personajes = Personaje.query.order_by(Personaje.nombre).all()
    return render_template('admin_regalar_poder.html', personajes=personajes)

@app.route('/admin/personaje/<int:personaje_id>/regalar-poder', methods=['POST'])
@admin_required
def regalar_poder_personaje(personaje_id):
    """Regalar poder a un personaje específico"""
    personaje = Personaje.query.get_or_404(personaje_id)
    cantidad = request.form.get('cantidad')
    
    if not cantidad or not cantidad.isdigit():
        flash('Debes ingresar una cantidad válida', 'error')
        return redirect(url_for('admin_regalar_poder'))
    
    cantidad = int(cantidad)
    if cantidad <= 0:
        flash('La cantidad debe ser mayor a 0', 'error')
        return redirect(url_for('admin_regalar_poder'))
    
    # Regalar poder al personaje
    personaje.poder_regalado += cantidad
    
    db.session.commit()
    
    # Actualizar rankings
    actualizar_rankings()
    
    flash(f'Se regalaron {cantidad} puntos de poder a {personaje.nombre}. Poder total actual: {personaje.poder_total}', 'success')
    return redirect(url_for('admin_regalar_poder'))

# ===== SISTEMA DE CLANES =====

@app.route('/clanes')
@login_required
def listar_clanes():
    """Listar todos los clanes disponibles"""
    clanes = Clan.query.filter_by(activo=True).order_by(Clan.nombre).all()
    user = Usuario.query.get(session['user_id'])
    
    # Obtener personaje activo si existe
    personaje_activo = None
    if 'personaje_activo_id' in session:
        personaje_activo = Personaje.query.get(session['personaje_activo_id'])
        # Verificar que el personaje activo pertenece al usuario
        if not personaje_activo or personaje_activo.creador_id != session['user_id']:
            personaje_activo = None
            session.pop('personaje_activo_id', None)
    
    # Si hay personaje activo, mostrar solo ese personaje
    if personaje_activo:
        personajes = [personaje_activo]
        mostrar_todos = False
    else:
        # Mostrar todos los personajes del usuario
        personajes = Personaje.query.filter_by(creador_id=user.id).all()
        mostrar_todos = True
    
    return render_template('clanes.html', clanes=clanes, personajes=personajes, personaje_activo=personaje_activo, mostrar_todos=mostrar_todos)

@app.route('/personaje/<int:personaje_id>/clanes')
@login_required
def clanes_personaje_contextual(personaje_id):
    """Clanes específicos para un personaje"""
    personaje = Personaje.query.get_or_404(personaje_id)
    
    # Verificar que el personaje pertenece al usuario
    user = Usuario.query.get(session['user_id'])
    if personaje.creador_id != user.id:
        flash('No puedes acceder a los clanes con personajes que no son tuyos', 'error')
        return redirect(url_for('index'))
    
    clanes = Clan.query.filter_by(activo=True).order_by(Clan.nombre).all()
    
    return render_template('clanes_personaje.html', clanes=clanes, personaje=personaje, user=user)

@app.route('/clan/<int:clan_id>')
def ver_clan(clan_id):
    """Ver información detallada de un clan"""
    clan = Clan.query.get_or_404(clan_id)
    # Obtener miembros con información de jerarquía
    membresias = MiembroClan.query.filter_by(clan_id=clan_id).join(MiembroClan.personaje).order_by(Personaje.nombre).all()
    
    return render_template('ver_clan.html', clan=clan, membresias=membresias)

@app.route('/clan/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_clan():
    """Crear un nuevo clan"""
    user = Usuario.query.get(session['user_id'])
    
    # Obtener personaje activo si existe
    personaje_activo = None
    if 'personaje_activo_id' in session:
        personaje_activo = Personaje.query.get(session['personaje_activo_id'])
        # Verificar que el personaje activo pertenece al usuario
        if not personaje_activo or personaje_activo.creador_id != session['user_id']:
            personaje_activo = None
            session.pop('personaje_activo_id', None)
    
    # Si hay personaje activo, mostrar solo ese personaje
    if personaje_activo:
        personajes = [personaje_activo]
        mostrar_todos = False
    else:
        # Mostrar todos los personajes del usuario
        personajes = Personaje.query.filter_by(creador_id=user.id).all()
        mostrar_todos = True
    
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        descripcion = request.form.get('descripcion')
        personaje_id = request.form.get('personaje_id')
        
        # Verificar que el personaje pertenece al usuario
        personaje = Personaje.query.filter_by(id=personaje_id, creador_id=user.id).first()
        if not personaje:
            flash('Personaje no válido', 'error')
            return redirect(url_for('nuevo_clan'))
        
        # Verificar que el personaje no pertenece ya a un clan
        if personaje.clan_id:
            flash('Este personaje ya pertenece a un clan', 'error')
            return redirect(url_for('nuevo_clan'))
        
        # Verificar que el usuario no ha creado ya un clan
        clan_existente = Clan.query.filter_by(creador_id=personaje_id).first()
        if clan_existente:
            flash('Ya has creado un clan con este personaje', 'error')
            return redirect(url_for('nuevo_clan'))
        
        # Manejar subida de insignia
        insignia_path = None
        if 'insignia' in request.files:
            file = request.files['insignia']
            if file.filename != '':
                if not allowed_file(file.filename):
                    flash('Formato de archivo no permitido. Use: PNG, JPG, JPEG, GIF, WEBP', 'error')
                    return redirect(request.url)
                
                filename = secure_filename(f"clan_{nombre}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{file.filename.rsplit('.', 1)[1].lower()}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                insignia_path = f"uploads/{filename}"
        
        # Crear el clan
        nuevo_clan = Clan(
            nombre=nombre,
            descripcion=descripcion,
            insignia=insignia_path,
            creador_id=personaje_id
        )
        
        db.session.add(nuevo_clan)
        db.session.flush()  # Para obtener el ID del clan
        
        # Asignar el personaje al clan como líder
        personaje.clan_id = nuevo_clan.id
        
        # Crear membresía del líder
        membresia_lider = MiembroClan(
            personaje_id=personaje_id,
            clan_id=nuevo_clan.id,
            jerarquia='lider',
            asignado_por=personaje_id
        )
        
        db.session.add(membresia_lider)
        db.session.commit()
        
        flash(f'¡Clan "{nombre}" creado exitosamente! {personaje.nombre} es ahora el líder.', 'success')
        return redirect(url_for('ver_clan', clan_id=nuevo_clan.id))
    
    return render_template('nuevo_clan.html', personajes=personajes)

@app.route('/clan/<int:clan_id>/solicitar', methods=['POST'])
@login_required
def solicitar_unirse_clan(clan_id):
    """Solicitar unirse a un clan"""
    clan = Clan.query.get_or_404(clan_id)
    user = Usuario.query.get(session['user_id'])
    personaje_id = request.form.get('personaje_id')
    mensaje = request.form.get('mensaje', '')
    
    # Verificar que el personaje pertenece al usuario
    personaje = Personaje.query.filter_by(id=personaje_id, creador_id=user.id).first()
    if not personaje:
        flash('Personaje no válido', 'error')
        return redirect(url_for('ver_clan', clan_id=clan_id))
    
    # Verificar que el personaje no pertenece ya a un clan
    if personaje.clan_id:
        flash('Este personaje ya pertenece a un clan', 'error')
        return redirect(url_for('ver_clan', clan_id=clan_id))
    
    # Verificar que no hay una solicitud pendiente
    solicitud_existente = SolicitudClan.query.filter_by(
        personaje_id=personaje_id, 
        clan_id=clan_id, 
        estado='pendiente'
    ).first()
    
    if solicitud_existente:
        flash('Ya tienes una solicitud pendiente para este clan', 'error')
        return redirect(url_for('ver_clan', clan_id=clan_id))
    
    # Crear solicitud
    nueva_solicitud = SolicitudClan(
        personaje_id=personaje_id,
        clan_id=clan_id,
        mensaje=mensaje
    )
    
    db.session.add(nueva_solicitud)
    db.session.commit()
    
    flash(f'Solicitud enviada al clan "{clan.nombre}". Espera la respuesta del líder.', 'success')
    return redirect(url_for('ver_clan', clan_id=clan_id))

@app.route('/clan/solicitudes')
@login_required
def solicitudes_clan():
    """Ver solicitudes de clan del usuario"""
    user = Usuario.query.get(session['user_id'])
    
    # Solicitudes enviadas por el usuario
    solicitudes_enviadas = SolicitudClan.query.join(Personaje).filter(
        Personaje.creador_id == user.id
    ).order_by(SolicitudClan.fecha_solicitud.desc()).all()
    
    # Solicitudes recibidas (si el usuario es líder de algún clan)
    solicitudes_recibidas = []
    # Obtener todos los personajes del usuario
    personajes_usuario = Personaje.query.filter_by(creador_id=user.id).all()
    # Obtener todos los clanes donde el usuario es líder (a través de cualquiera de sus personajes)
    clanes_lider = Clan.query.filter(Clan.creador_id.in_([p.id for p in personajes_usuario])).all()
    for clan in clanes_lider:
        solicitudes = SolicitudClan.query.filter_by(clan_id=clan.id, estado='pendiente').all()
        solicitudes_recibidas.extend(solicitudes)
    
    return render_template('solicitudes_clan.html', 
                         solicitudes_enviadas=solicitudes_enviadas,
                         solicitudes_recibidas=solicitudes_recibidas)

@app.route('/solicitud-clan/<int:solicitud_id>/aceptar', methods=['POST'])
@login_required
def aceptar_solicitud_clan(solicitud_id):
    """Aceptar solicitud de unirse al clan"""
    solicitud = SolicitudClan.query.get_or_404(solicitud_id)
    user = Usuario.query.get(session['user_id'])
    
    # Verificar que el usuario es líder del clan
    clan = Clan.query.get(solicitud.clan_id)
    if not clan:
        flash('Clan no encontrado', 'error')
        return redirect(url_for('solicitudes_clan'))
    
    # Verificar que el usuario es líder del clan (a través de cualquiera de sus personajes)
    personajes_usuario = Personaje.query.filter_by(creador_id=user.id).all()
    if clan.creador_id not in [p.id for p in personajes_usuario]:
        flash('No tienes permisos para aceptar solicitudes de este clan', 'error')
        return redirect(url_for('solicitudes_clan'))
    
    # Verificar que la solicitud está pendiente
    if solicitud.estado != 'pendiente':
        flash('Esta solicitud ya fue procesada', 'error')
        return redirect(url_for('solicitudes_clan'))
    
    # Aceptar la solicitud
    solicitud.estado = 'aceptada'
    solicitud.fecha_respuesta = datetime.utcnow()
    
    # Asignar el personaje al clan
    personaje = Personaje.query.get(solicitud.personaje_id)
    personaje.clan_id = clan.id
    
    # Crear membresía
    membresia = MiembroClan(
        personaje_id=personaje.id,
        clan_id=clan.id,
        jerarquia='miembro',
        asignado_por=clan.creador_id
    )
    
    db.session.add(membresia)
    db.session.commit()
    
    flash(f'{personaje.nombre} se ha unido al clan "{clan.nombre}"', 'success')
    return redirect(url_for('solicitudes_clan'))

@app.route('/solicitud-clan/<int:solicitud_id>/rechazar', methods=['POST'])
@login_required
def rechazar_solicitud_clan(solicitud_id):
    """Rechazar solicitud de unirse al clan"""
    solicitud = SolicitudClan.query.get_or_404(solicitud_id)
    user = Usuario.query.get(session['user_id'])
    
    # Verificar que el usuario es líder del clan
    clan = Clan.query.get(solicitud.clan_id)
    if not clan:
        flash('Clan no encontrado', 'error')
        return redirect(url_for('solicitudes_clan'))
    
    # Verificar que el usuario es líder del clan (a través de cualquiera de sus personajes)
    personajes_usuario = Personaje.query.filter_by(creador_id=user.id).all()
    if clan.creador_id not in [p.id for p in personajes_usuario]:
        flash('No tienes permisos para rechazar solicitudes de este clan', 'error')
        return redirect(url_for('solicitudes_clan'))
    
    # Rechazar la solicitud
    solicitud.estado = 'rechazada'
    solicitud.fecha_respuesta = datetime.utcnow()
    
    db.session.commit()
    
    personaje = Personaje.query.get(solicitud.personaje_id)
    flash(f'Solicitud de {personaje.nombre} rechazada', 'success')
    return redirect(url_for('solicitudes_clan'))

@app.route('/clan/<int:clan_id>/gestionar')
@login_required
def gestionar_clan(clan_id):
    """Panel de gestión del clan (solo para líderes)"""
    clan = Clan.query.get_or_404(clan_id)
    user = Usuario.query.get(session['user_id'])
    
    # Verificar que el usuario es líder del clan
    if not clan:
        flash('Clan no encontrado', 'error')
        return redirect(url_for('listar_clanes'))
    
    # Verificar que el usuario es líder del clan (a través de cualquiera de sus personajes)
    personajes_usuario = Personaje.query.filter_by(creador_id=user.id).all()
    if clan.creador_id not in [p.id for p in personajes_usuario]:
        flash('No tienes permisos para gestionar este clan', 'error')
        return redirect(url_for('listar_clanes'))
    
    miembros = MiembroClan.query.filter_by(clan_id=clan_id).order_by(MiembroClan.jerarquia, MiembroClan.fecha_ingreso).all()
    solicitudes_pendientes = SolicitudClan.query.filter_by(clan_id=clan_id, estado='pendiente').all()
    
    return render_template('gestionar_clan.html', 
                         clan=clan, 
                         miembros=miembros, 
                         solicitudes_pendientes=solicitudes_pendientes)

@app.route('/clan/<int:clan_id>/cambiar-jerarquia/<int:personaje_id>', methods=['POST'])
@login_required
def cambiar_jerarquia_clan(clan_id, personaje_id):
    """Cambiar jerarquía de un miembro del clan"""
    clan = Clan.query.get_or_404(clan_id)
    user = Usuario.query.get(session['user_id'])
    nueva_jerarquia = request.form.get('jerarquia')
    
    # Verificar que el usuario es líder del clan
    if not clan:
        flash('Clan no encontrado', 'error')
        return redirect(url_for('gestionar_clan', clan_id=clan_id))
    
    # Verificar que el usuario es líder del clan (a través de cualquiera de sus personajes)
    personajes_usuario = Personaje.query.filter_by(creador_id=user.id).all()
    if clan.creador_id not in [p.id for p in personajes_usuario]:
        flash('No tienes permisos para cambiar jerarquías en este clan', 'error')
        return redirect(url_for('gestionar_clan', clan_id=clan_id))
    
    # Verificar que el personaje pertenece al clan
    membresia = MiembroClan.query.filter_by(clan_id=clan_id, personaje_id=personaje_id).first()
    if not membresia:
        flash('Este personaje no pertenece al clan', 'error')
        return redirect(url_for('gestionar_clan', clan_id=clan_id))
    
    # Cambiar jerarquía
    membresia.jerarquia = nueva_jerarquia
    membresia.asignado_por = clan.creador_id
    
    db.session.commit()
    
    personaje = Personaje.query.get(personaje_id)
    flash(f'Jerarquía de {personaje.nombre} cambiada a {nueva_jerarquia.title()}', 'success')
    return redirect(url_for('gestionar_clan', clan_id=clan_id))

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

# Sistema de Misiones
@app.route('/misiones')
@login_required
def listar_misiones():
    """Listar misiones disponibles para el usuario"""
    user = Usuario.query.get(session['user_id'])
    
    # Obtener personaje activo si existe
    personaje_activo = None
    if 'personaje_activo_id' in session:
        personaje_activo = Personaje.query.get(session['personaje_activo_id'])
        # Verificar que el personaje activo pertenece al usuario
        if not personaje_activo or personaje_activo.creador_id != session['user_id']:
            personaje_activo = None
            session.pop('personaje_activo_id', None)
    
    # Si hay personaje activo, mostrar solo ese personaje
    if personaje_activo:
        personajes = [personaje_activo]
        mostrar_todos = False
    else:
        # Mostrar todos los personajes del usuario
        personajes = Personaje.query.filter_by(creador_id=user.id).all()
        mostrar_todos = True
    
    # Obtener misiones activas (filtrar nulas)
    misiones_activas = [m for m in Mision.query.filter_by(activa=True).order_by(Mision.poder_minimo).all() if m is not None]
    
    # Obtener misiones en progreso del usuario
    misiones_en_progreso = {}
    for personaje in personajes:
        mision_activa = MisionPersonaje.query.filter_by(
            personaje_id=personaje.id, 
            estado='en_progreso'
        ).first()
        if mision_activa:
            misiones_en_progreso[personaje.id] = mision_activa
    
    return render_template('misiones.html', 
                         misiones=misiones_activas, 
                         personajes=personajes,
                         misiones_en_progreso=misiones_en_progreso,
                         personaje_activo=personaje_activo,
                         mostrar_todos=mostrar_todos)

@app.route('/personaje/<int:personaje_id>/misiones')
@login_required
def misiones_personaje_contextual(personaje_id):
    """Misiones específicas para un personaje"""
    personaje = Personaje.query.get_or_404(personaje_id)
    
    # Verificar que el personaje pertenece al usuario
    user = Usuario.query.get(session['user_id'])
    if personaje.creador_id != user.id:
        flash('No puedes acceder a las misiones con personajes que no son tuyos', 'error')
        return redirect(url_for('index'))
    
    # Obtener misiones activas (filtrar nulas)
    misiones_activas = [m for m in Mision.query.filter_by(activa=True).order_by(Mision.poder_minimo).all() if m is not None]
    
    # Obtener misión en progreso del personaje
    mision_en_progreso = MisionPersonaje.query.filter_by(
        personaje_id=personaje.id, 
        estado='en_progreso'
    ).first()
    
    return render_template('misiones_personaje.html', 
                         misiones=misiones_activas, 
                         personaje=personaje,
                         mision_en_progreso=mision_en_progreso,
                         user=user)

@app.route('/mision/<int:mision_id>/aceptar', methods=['POST'])
@login_required
def aceptar_mision(mision_id):
    print('--- aceptar_mision llamada ---')
    personaje_id = request.form.get('personaje_id')
    print(f'personaje_id recibido: {personaje_id}')
    user = Usuario.query.get(session['user_id'])
    personaje = Personaje.query.filter_by(id=personaje_id, creador_id=user.id).first()
    print(f'personaje encontrado: {personaje}')
    if not personaje:
        print('Personaje no encontrado')
        flash('Personaje no encontrado', 'error')
        return redirect(url_for('listar_misiones'))
    mision_activa = MisionPersonaje.query.filter_by(
        personaje_id=personaje_id, 
        estado='en_progreso'
    ).first()
    print(f'mision_activa: {mision_activa}')
    if mision_activa:
        print('Ya tiene misión activa')
        flash('Este personaje ya tiene una misión en progreso', 'error')
        return redirect(url_for('listar_misiones'))
    mision = Mision.query.get_or_404(mision_id)
    print(f'mision encontrada: {mision}')
    if not mision.activa:
        print('Misión no activa')
        flash('Esta misión no está disponible', 'error')
        return redirect(url_for('listar_misiones'))
    poder_personaje = personaje.calcular_poder()
    print(f'poder_personaje: {poder_personaje}, poder_minimo: {mision.poder_minimo}')
    if poder_personaje < mision.poder_minimo:
        print('Poder insuficiente')
        flash(f'Tu personaje necesita al menos {mision.poder_minimo} de poder para esta misión', 'error')
        return redirect(url_for('listar_misiones'))
    from datetime import timedelta
    fecha_expiracion = datetime.utcnow() + timedelta(seconds=mision.duracion_segundos)
    nueva_mision_personaje = MisionPersonaje(
        personaje_id=personaje_id,
        mision_id=mision_id,
        fecha_expiracion=fecha_expiracion
    )
    db.session.add(nueva_mision_personaje)
    db.session.commit()
    print('Misión aceptada y guardada')
    minutos = mision.duracion_segundos // 60
    segundos = mision.duracion_segundos % 60
    tiempo_texto = f"{minutos}m {segundos}s" if minutos > 0 else f"{segundos}s"
    flash(f'Misión "{mision.titulo}" aceptada. Tiempo límite: {tiempo_texto}', 'success')
    return redirect(url_for('listar_misiones'))

@app.route('/mision/completar', methods=['POST'])
@login_required
def completar_mision():
    """Completar una misión en progreso"""
    personaje_id = request.form.get('personaje_id')
    
    # Verificar que el personaje pertenece al usuario
    user = Usuario.query.get(session['user_id'])
    personaje = Personaje.query.filter_by(id=personaje_id, creador_id=user.id).first()
    
    if not personaje:
        flash('Personaje no encontrado', 'error')
        return redirect(url_for('listar_misiones'))
    
    # Obtener la misión en progreso
    mision_personaje = MisionPersonaje.query.filter_by(
        personaje_id=personaje_id, 
        estado='en_progreso'
    ).first()
    
    if not mision_personaje:
        flash('No tienes una misión en progreso', 'error')
        return redirect(url_for('listar_misiones'))
    
    # Verificar si la misión ha expirado
    if mision_personaje.fecha_expiracion and datetime.utcnow() > mision_personaje.fecha_expiracion:
        # La misión ha expirado, pero permitimos completarla para dar recompensas
        print(f'Misión expirada, pero permitiendo completar para dar recompensas')
        # NO marcamos como expirada aquí, permitimos que se complete
    
    # Verificar que ha transcurrido el tiempo mínimo para completar la misión
    print(f'--- completar_mision llamada ---')
    print(f'personaje_id: {personaje_id}')
    print(f'fecha_expiracion: {mision_personaje.fecha_expiracion}')
    print(f'datetime.utcnow(): {datetime.utcnow()}')
    
    if mision_personaje.fecha_expiracion and datetime.utcnow() < mision_personaje.fecha_expiracion:
        tiempo_restante = (mision_personaje.fecha_expiracion - datetime.utcnow()).total_seconds()
        minutos_restantes = int(tiempo_restante // 60)
        segundos_restantes = int(tiempo_restante % 60)
        print(f'Tiempo restante: {minutos_restantes}m {segundos_restantes}s - NO se puede completar aún')
        flash(f'Debes esperar {minutos_restantes}m {segundos_restantes}s para completar esta misión', 'error')
        return redirect(url_for('listar_misiones'))
    
    print(f'Puede completar la misión - asignando recompensas')
    print(f'Rastamonios antes: {personaje.rastamonios}')
    print(f'Poder antes: {personaje.poder_total}')
    print(f'Recompensa rastamonios: {mision_personaje.mision.recompensa_rastamonios}')
    print(f'Recompensa poder: {mision_personaje.mision.recompensa_poder}')
    
    # Completar la misión
    mision_personaje.estado = 'completada'
    mision_personaje.fecha_completada = datetime.utcnow()
    
    # Dar recompensas
    personaje.rastamonios += mision_personaje.mision.recompensa_rastamonios
    personaje.poder_misiones += mision_personaje.mision.recompensa_poder
    
    print(f'Rastamonios después: {personaje.rastamonios}')
    print(f'Poder después: {personaje.poder_total}')
    
    db.session.commit()
    print(f'Base de datos actualizada')
    
    # Actualizar rankings
    actualizar_rankings()
    print(f'Rankings actualizados')
    
    flash(f'Misión completada! Recompensa: {mision_personaje.mision.recompensa_rastamonios} rastamonios y +{mision_personaje.mision.recompensa_poder} poder', 'success')
    print(f'Flash message enviado')
    return redirect(url_for('listar_misiones'))

@app.route('/mision/abandonar', methods=['POST'])
@login_required
def abandonar_mision():
    """Abandonar una misión en progreso"""
    personaje_id = request.form.get('personaje_id')
    
    # Verificar que el personaje pertenece al usuario
    user = Usuario.query.get(session['user_id'])
    personaje = Personaje.query.filter_by(id=personaje_id, creador_id=user.id).first()
    
    if not personaje:
        flash('Personaje no encontrado', 'error')
        return redirect(url_for('listar_misiones'))
    
    # Obtener la misión en progreso
    mision_personaje = MisionPersonaje.query.filter_by(
        personaje_id=personaje_id, 
        estado='en_progreso'
    ).first()
    
    if not mision_personaje:
        flash('No tienes una misión en progreso', 'error')
        return redirect(url_for('listar_misiones'))
    
    # Abandonar la misión
    mision_personaje.estado = 'fallida'
    db.session.commit()
    
    flash('Misión abandonada', 'info')
    return redirect(url_for('listar_misiones'))

# Rutas de administración para misiones
@app.route('/admin/misiones')
@admin_required
def admin_misiones():
    """Panel de administración de misiones"""
    # Filtrar misiones nulas
    misiones = [m for m in Mision.query.order_by(Mision.fecha_creacion.desc()).all() if m is not None]
    return render_template('admin_misiones.html', misiones=misiones)

@app.route('/admin/mision/nueva', methods=['GET', 'POST'])
@admin_required
def nueva_mision():
    """Crear nueva misión"""
    if request.method == 'POST':
        titulo = request.form.get('titulo')
        descripcion = request.form.get('descripcion')
        poder_minimo = int(request.form.get('poder_minimo'))
        recompensa_poder = int(request.form.get('recompensa_poder'))
        recompensa_rastamonios = int(request.form.get('recompensa_rastamonios'))
        duracion_segundos = int(request.form.get('duracion_segundos'))
        
        # Manejar subida de imagen (opcional)
        imagen_path = None
        if 'imagen' in request.files:
            file = request.files['imagen']
            if file.filename != '':
                if not allowed_file(file.filename):
                    flash('Formato de archivo no permitido. Use: PNG, JPG, JPEG, GIF, WEBP', 'error')
                    return redirect(request.url)
                
                filename = secure_filename(f"mision_{titulo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{file.filename.rsplit('.', 1)[1].lower()}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                imagen_path = f'uploads/{filename}'
        
        nueva_mision = Mision(
            titulo=titulo,
            descripcion=descripcion,
            imagen=imagen_path,
            poder_minimo=poder_minimo,
            recompensa_poder=recompensa_poder,
            recompensa_rastamonios=recompensa_rastamonios,
            duracion_segundos=duracion_segundos
        )
        
        db.session.add(nueva_mision)
        db.session.commit()
        
        flash('Misión creada exitosamente', 'success')
        return redirect(url_for('admin_misiones'))
    
    return render_template('nueva_mision.html')

@app.route('/admin/mision/<int:mision_id>/editar', methods=['GET', 'POST'])
@admin_required
def editar_mision(mision_id):
    """Editar misión existente"""
    mision = Mision.query.get_or_404(mision_id)
    
    if request.method == 'POST':
        mision.titulo = request.form.get('titulo')
        mision.descripcion = request.form.get('descripcion')
        mision.poder_minimo = int(request.form.get('poder_minimo'))
        mision.recompensa_poder = int(request.form.get('recompensa_poder'))
        mision.recompensa_rastamonios = int(request.form.get('recompensa_rastamonios'))
        mision.duracion_segundos = int(request.form.get('duracion_segundos'))
        
        # Manejar nueva imagen (opcional)
        if 'imagen' in request.files:
            file = request.files['imagen']
            if file.filename != '':
                if not allowed_file(file.filename):
                    flash('Formato de archivo no permitido. Use: PNG, JPG, JPEG, GIF, WEBP', 'error')
                    return redirect(request.url)
                
                filename = secure_filename(f"mision_{mision.titulo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{file.filename.rsplit('.', 1)[1].lower()}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                mision.imagen = f'uploads/{filename}'
        
        db.session.commit()
        
        flash('Misión actualizada exitosamente', 'success')
        return redirect(url_for('admin_misiones'))
    
    return render_template('editar_mision.html', mision=mision)

@app.route('/admin/mision/<int:mision_id>/toggle', methods=['POST'])
@admin_required
def toggle_mision(mision_id):
    """Activar/desactivar misión"""
    mision = Mision.query.get_or_404(mision_id)
    mision.activa = not mision.activa
    
    db.session.commit()
    
    estado = "activada" if mision.activa else "desactivada"
    flash(f'Misión {estado} exitosamente', 'success')
    return redirect(url_for('admin_misiones'))

@app.route('/admin/mision/<int:mision_id>/eliminar', methods=['POST'])
@admin_required
def eliminar_mision(mision_id):
    """Eliminar misión"""
    mision = Mision.query.get_or_404(mision_id)
    
    # Verificar que no hay misiones activas usando esta misión
    misiones_activas = MisionPersonaje.query.filter_by(mision_id=mision_id, estado='en_progreso').count()
    if misiones_activas > 0:
        flash('No se puede eliminar una misión que tiene personajes activos', 'error')
        return redirect(url_for('admin_misiones'))
    
    db.session.delete(mision)
    db.session.commit()
    
    flash('Misión eliminada exitosamente', 'success')
    return redirect(url_for('admin_misiones'))

# API para verificar estado de misiones en tiempo real
@app.route('/api/mision/estado/<int:personaje_id>')
@login_required
def estado_mision(personaje_id):
    """API para obtener el estado de la misión de un personaje"""
    user = Usuario.query.get(session['user_id'])
    personaje = Personaje.query.filter_by(id=personaje_id, creador_id=user.id).first()
    
    if not personaje:
        return jsonify({'error': 'Personaje no encontrado'}), 404
    
    mision_personaje = MisionPersonaje.query.filter_by(
        personaje_id=personaje_id, 
        estado='en_progreso'
    ).first()
    
    if not mision_personaje:
        return jsonify({'estado': 'sin_mision'})
    
    # Calcular tiempo restante
    tiempo_restante = None
    if mision_personaje.fecha_expiracion:
        tiempo_restante = (mision_personaje.fecha_expiracion - datetime.utcnow()).total_seconds()
        
        if tiempo_restante <= 0:
            # La misión ha expirado, pero no la marcamos automáticamente
            # Permitimos que el usuario la complete manualmente
            return jsonify({'estado': 'expirada', 'tiempo_restante': 0})
    
    return jsonify({
        'estado': 'en_progreso',
        'mision': {
            'titulo': mision_personaje.mision.titulo,
            'tiempo_restante': tiempo_restante,
            'fecha_expiracion': mision_personaje.fecha_expiracion.isoformat() if mision_personaje.fecha_expiracion else None
        }
    })

@app.route('/tienda/item/<int:item_id>', methods=['GET', 'POST'])
@login_required
def ver_item_tienda(item_id):
    item = TiendaItem.query.get_or_404(item_id)
    user = Usuario.query.get(session['user_id'])
    personajes = Personaje.query.filter_by(creador_id=user.id).all() if not user.es_admin else Personaje.query.all()
    mensaje = None
    comprado_por = set()
    
    # Verificar si hay una compra en venta para este ítem
    compra_en_venta = None
    if item.es_unico:
        compra_en_venta = Compra.query.filter_by(item_id=item.id, en_venta=True).first()
    
    for p in personajes:
        compra = Compra.query.filter_by(personaje_id=p.id, item_id=item.id).first()
        if compra:
            comprado_por.add(p.id)
    
    if request.method == 'POST':
        personaje_id = request.form.get('personaje_id')
        personaje = Personaje.query.get_or_404(personaje_id)
        # Verificar si ya lo compró
        compra_existente = Compra.query.filter_by(personaje_id=personaje.id, item_id=item.id).first()
        if compra_existente:
            mensaje = 'Este personaje ya ha comprado este ítem. Solo puedes comprarlo una vez.'
        else:
            # Redirigir a la lógica de compra original, pero solo para este ítem y personaje
            return redirect(url_for('comprar_item_unico', personaje_id=personaje.id, item_id=item.id))
    
    return render_template('ver_item_tienda.html', item=item, personajes=personajes, comprado_por=comprado_por, mensaje=mensaje, compra_en_venta=compra_en_venta)

@app.route('/tienda/comprar/<int:personaje_id>/<int:item_id>', methods=['GET'])
@login_required
def comprar_item_unico(personaje_id, item_id):
    # Lógica de compra igual que en comprar_item, pero solo para 1 unidad y sin formulario
    personaje = Personaje.query.get_or_404(personaje_id)
    item = TiendaItem.query.get_or_404(item_id)
    cantidad = 1
    # Verificar si el personaje ya tiene este item
    compra_existente = Compra.query.filter_by(personaje_id=personaje.id, item_id=item.id).first()
    if compra_existente:
        flash('Este personaje ya ha comprado este ítem. Solo puedes comprarlo una vez.', 'error')
        return redirect(url_for('ver_item_tienda', item_id=item.id))
    if not item.disponible:
        flash('Este item no está disponible para compra.', 'error')
        return redirect(url_for('ver_item_tienda', item_id=item.id))
    if item.es_unico:
        # Verificar si hay una compra en venta para este ítem
        compra_en_venta = Compra.query.filter_by(item_id=item.id, en_venta=True).first()
        if compra_en_venta:
            # Si está en venta, redirigir a la función de compra de ítems únicos en venta
            flash('Este ítem único está en venta. Usa el formulario de compra de ítem en venta.', 'error')
            return redirect(url_for('ver_item_tienda', item_id=item.id))
        
        # Si no está en venta, verificar si ya fue comprado
        compras_existentes = Compra.query.filter_by(item_id=item.id).count()
        if compras_existentes > 0:
            flash('Este item único ya ha sido comprado por otro personaje.', 'error')
            return redirect(url_for('ver_item_tienda', item_id=item.id))
    else:
        if item.stock >= 0:
            if item.stock < cantidad:
                flash(f'No hay suficiente stock. Solo quedan {item.stock} unidades disponibles.', 'error')
                return redirect(url_for('ver_item_tienda', item_id=item.id))
    total_items_personaje = Compra.query.filter_by(personaje_id=personaje.id).count()
    if total_items_personaje + cantidad > 33:
        flash(f'No puedes comprar más items. Tu personaje ya tiene {total_items_personaje} items y el límite es 33.', 'error')
        return redirect(url_for('ver_item_tienda', item_id=item.id))
    total = item.precio * cantidad
    if personaje.rastamonios < total:
        flash('No tienes suficientes rastamonios para esta compra.', 'error')
        return redirect(url_for('ver_item_tienda', item_id=item.id))
    personaje.rastamonios -= total
    compra = Compra(personaje_id=personaje.id, item_id=item.id, cantidad=cantidad)
    db.session.add(compra)
    if item.es_unico:
        item.disponible = False
    else:
        if item.stock >= 0:
            item.stock -= cantidad
            if item.stock <= 0:
                item.disponible = False
    actualizar_rankings()
    db.session.commit()
    flash(f'¡Compra exitosa! Has adquirido {item.nombre}.', 'success')
    return redirect(url_for('ver_item_tienda', item_id=item.id))

@app.route('/tienda/comprar_unico_en_venta/<int:compra_id>/<int:personaje_id>', methods=['POST'])
@login_required
def comprar_unico_en_venta(compra_id, personaje_id):
    compra = Compra.query.get_or_404(compra_id)
    # Usar el personaje_id del formulario en lugar del parámetro de la URL
    personaje_id_form = request.form.get('personaje_id')
    if not personaje_id_form:
        flash('Debes seleccionar un personaje para comprar.', 'error')
        return redirect(url_for('ver_item_tienda', item_id=compra.item_id))
    personaje = Personaje.query.get_or_404(personaje_id_form)
    
    # Verificaciones adicionales
    if not compra.en_venta or not compra.item.es_unico:
        flash('Este ítem no está disponible para compra como único en venta.', 'error')
        return redirect(url_for('ver_item_tienda', item_id=compra.item_id))
    
    # Verificar que el ítem esté disponible
    if not compra.item.disponible:
        flash('Este ítem no está disponible para compra.', 'error')
        return redirect(url_for('ver_item_tienda', item_id=compra.item_id))
    
    if compra.vendedor_id == personaje.id:
        flash('No puedes comprar tu propio ítem único en venta.', 'error')
        return redirect(url_for('ver_item_tienda', item_id=compra.item_id))
    
    if personaje.rastamonios < compra.precio_venta:
        flash('No tienes suficientes rastamonios para esta compra.', 'error')
        return redirect(url_for('ver_item_tienda', item_id=compra.item_id))
    
    # Verificar que el personaje no tenga ya este ítem
    compra_existente = Compra.query.filter_by(personaje_id=personaje.id, item_id=compra.item_id).first()
    if compra_existente:
        flash('Este personaje ya tiene este ítem. Solo puedes comprarlo una vez.', 'error')
        return redirect(url_for('ver_item_tienda', item_id=compra.item_id))
    
    # Transferir el ítem: cambiar el personaje dueño, quitar en_venta, pagar al vendedor
    vendedor = Personaje.query.get(compra.vendedor_id)
    personaje.rastamonios -= compra.precio_venta
    if vendedor:
        vendedor.rastamonios += compra.precio_venta
    
    compra.personaje_id = personaje.id
    compra.en_venta = False
    compra.precio_venta = None
    compra.vendedor_id = None
    compra.fecha = datetime.utcnow()
    
    # Actualizar rankings ya que el personaje ganó poder
    actualizar_rankings()
    
    db.session.commit()
    flash(f'¡Compra exitosa! Ahora {compra.item.nombre} pertenece a {personaje.nombre}.', 'success')
    return redirect(url_for('ver_personaje', personaje_id=personaje.id))

@app.route('/tienda/editar_precio_unico/<int:compra_id>', methods=['GET', 'POST'])
@login_required
def editar_precio_unico(compra_id):
    compra = Compra.query.get_or_404(compra_id)
    user = Usuario.query.get(session['user_id'])
    personaje = Personaje.query.get(compra.vendedor_id)
    if not compra.en_venta or not compra.item.es_unico or not personaje or personaje.creador_id != user.id:
        flash('No tienes permisos para editar el precio de este ítem.', 'error')
        return redirect(url_for('tienda'))
    if request.method == 'POST':
        nuevo_precio = request.form.get('nuevo_precio')
        if not nuevo_precio or not nuevo_precio.isdigit() or int(nuevo_precio) < 0:
            flash('Debes ingresar un precio válido.', 'error')
            return redirect(url_for('editar_precio_unico', compra_id=compra_id))
        compra.precio_venta = int(nuevo_precio)
        db.session.commit()
        flash('Precio actualizado correctamente.', 'success')
        return redirect(url_for('ver_personaje', personaje_id=compra.vendedor_id))
    return render_template('editar_precio_unico.html', compra=compra)

# ===== SISTEMA DE ATAQUES =====

@app.route('/ataques')
@login_required
def ataques():
    """Página principal de ataques disponibles"""
    # Obtener todos los ataques disponibles
    ataques_disponibles = Ataque.query.filter_by(disponible=True).all()
    
    # Filtrar ataques únicos que ya han sido comprados
    ataques_filtrados = []
    for ataque in ataques_disponibles:
        if ataque.es_unico:
            # Para ataques únicos, verificar si ya han sido comprados
            ataque_comprado = AtaquePersonaje.query.filter_by(ataque_id=ataque.id).first()
            if not ataque_comprado:
                # Si no ha sido comprado, está disponible
                ataques_filtrados.append(ataque)
            elif ataque_comprado.en_venta:
                # Si está en venta, está disponible para compra
                ataques_filtrados.append(ataque)
        else:
            # Para ataques no únicos, siempre están disponibles si tienen stock
            ataques_filtrados.append(ataque)
    
    user = Usuario.query.get(session['user_id'])
    
    # Obtener personaje activo si existe
    personaje_activo = None
    if 'personaje_activo_id' in session:
        personaje_activo = Personaje.query.get(session['personaje_activo_id'])
        # Verificar que el personaje activo pertenece al usuario
        if not personaje_activo or personaje_activo.creador_id != session['user_id']:
            personaje_activo = None
            session.pop('personaje_activo_id', None)
    
    # Si hay personaje activo, mostrar solo ese personaje
    if personaje_activo:
        personajes = [personaje_activo]
        mostrar_todos = False
    else:
        # Mostrar todos los personajes del usuario
        personajes = Personaje.query.filter_by(creador_id=user.id).all()
        mostrar_todos = True
    
    return render_template('ataques.html', ataques=ataques_filtrados, personajes=personajes, user=user, personaje_activo=personaje_activo, mostrar_todos=mostrar_todos)

@app.route('/personaje/<int:personaje_id>/ataques')
@login_required
def ataques_personaje_contextual(personaje_id):
    """Ataques específicos para un personaje"""
    personaje = Personaje.query.get_or_404(personaje_id)
    
    # Verificar que el personaje pertenece al usuario
    user = Usuario.query.get(session['user_id'])
    if personaje.creador_id != user.id:
        flash('No puedes acceder a los ataques con personajes que no son tuyos', 'error')
        return redirect(url_for('index'))
    
    # Obtener todos los ataques disponibles
    ataques_disponibles = Ataque.query.filter_by(disponible=True).all()
    
    # Filtrar ataques únicos que ya han sido comprados
    ataques_filtrados = []
    for ataque in ataques_disponibles:
        if ataque.es_unico:
            # Para ataques únicos, verificar si ya han sido comprados
            ataque_comprado = AtaquePersonaje.query.filter_by(ataque_id=ataque.id).first()
            if not ataque_comprado:
                # Si no ha sido comprado, está disponible
                ataques_filtrados.append(ataque)
            elif ataque_comprado.en_venta:
                # Si está en venta, está disponible para compra
                ataques_filtrados.append(ataque)
        else:
            # Para ataques no únicos, siempre están disponibles si tienen stock
            ataques_filtrados.append(ataque)
    
    return render_template('ataques_personaje.html', ataques=ataques_filtrados, personaje=personaje, user=user)

@app.route('/ataque/<int:ataque_id>')
@login_required
def ver_ataque(ataque_id):
    """Ver detalles de un ataque específico"""
    ataque = Ataque.query.get_or_404(ataque_id)
    
    # Verificar si el ataque único ya fue comprado y no está en venta
    if ataque.es_unico:
        ataque_comprado = AtaquePersonaje.query.filter_by(ataque_id=ataque.id).first()
        if ataque_comprado and not ataque_comprado.en_venta:
            flash('Este ataque único ya ha sido comprado y no está disponible en la tienda', 'error')
            return redirect(url_for('ataques'))
    
    user = Usuario.query.get(session['user_id'])
    
    # Obtener personaje activo si existe
    personaje_activo = None
    if 'personaje_activo_id' in session:
        personaje_activo = Personaje.query.get(session['personaje_activo_id'])
        # Verificar que el personaje activo pertenece al usuario
        if not personaje_activo or personaje_activo.creador_id != session['user_id']:
            personaje_activo = None
            session.pop('personaje_activo_id', None)
    
    # Si hay personaje activo, mostrar solo ese personaje
    if personaje_activo:
        personajes = [personaje_activo]
        mostrar_todos = False
    else:
        # Mostrar todos los personajes del usuario
        personajes = Personaje.query.filter_by(creador_id=user.id).all()
        mostrar_todos = True
    
    return render_template('ver_ataque.html', ataque=ataque, personajes=personajes, user=user, personaje_activo=personaje_activo, mostrar_todos=mostrar_todos)

@app.route('/ataque/comprar/<int:ataque_id>/<int:personaje_id>', methods=['POST'])
@login_required
def comprar_ataque(ataque_id, personaje_id):
    """Comprar un ataque para un personaje"""
    ataque = Ataque.query.get_or_404(ataque_id)
    personaje = Personaje.query.get_or_404(personaje_id)
    
    # Verificar que el personaje pertenece al usuario
    user = Usuario.query.get(session['user_id'])
    if personaje.creador_id != user.id:
        flash('No puedes comprar ataques para personajes que no son tuyos', 'error')
        return redirect(url_for('ataques'))
    
    # Verificar que el ataque está disponible
    if not ataque.disponible:
        flash('Este ataque no está disponible', 'error')
        return redirect(url_for('ver_ataque', ataque_id=ataque_id))
    
    # Verificar stock del ataque
    if ataque.stock != -1 and ataque.stock <= 0:
        flash('Este ataque está agotado', 'error')
        return redirect(url_for('ver_ataque', ataque_id=ataque_id))
    
    # Verificar si el ataque único ya fue comprado y no está en venta
    if ataque.es_unico:
        ataque_comprado = AtaquePersonaje.query.filter_by(ataque_id=ataque.id).first()
        if ataque_comprado and not ataque_comprado.en_venta:
            flash('Este ataque único ya ha sido comprado y no está disponible', 'error')
            return redirect(url_for('ver_ataque', ataque_id=ataque_id))
    
    # Verificar que el personaje no ya tiene este ataque específico
    ataque_existente = AtaquePersonaje.query.filter_by(
        personaje_id=personaje.id, 
        ataque_id=ataque.id
    ).first()
    if ataque_existente:
        flash('Este personaje ya tiene este ataque', 'error')
        return redirect(url_for('ver_ataque', ataque_id=ataque_id))
    
    # Verificar que el personaje tiene suficientes rastamonios
    if personaje.rastamonios < ataque.precio:
        flash('No tienes suficientes rastamonios para comprar este ataque', 'error')
        return redirect(url_for('ver_ataque', ataque_id=ataque_id))
    
    # Verificar límite de 50 ataques por personaje
    ataques_actuales = AtaquePersonaje.query.filter_by(personaje_id=personaje.id).count()
    if ataques_actuales >= 50:
        flash('Este personaje ya tiene el límite máximo de 50 ataques', 'error')
        return redirect(url_for('ver_ataque', ataque_id=ataque_id))
    
    # Verificar si el ataque requiere un clan específico
    if ataque.clan_requerido:
        if not personaje.clan_id or personaje.clan_id != ataque.clan_requerido:
            clan_requerido = Clan.query.get(ataque.clan_requerido)
            flash(f'Este ataque es exclusivo del clan "{clan_requerido.nombre}". Debes pertenecer a este clan para comprarlo.', 'error')
            return redirect(url_for('ver_ataque', ataque_id=ataque_id))
    
    # Realizar la compra
    personaje.rastamonios -= ataque.precio
    
    # Descontar stock si no es ilimitado
    if ataque.stock != -1:
        ataque.stock -= 1
    
    # Si es un ataque único, marcarlo como no disponible en la tienda
    if ataque.es_unico:
        ataque.disponible = False
    
    ataque_personaje = AtaquePersonaje(
        personaje_id=personaje.id,
        ataque_id=ataque.id,
        precio_compra=ataque.precio
    )
    
    db.session.add(ataque_personaje)
    db.session.commit()
    
    # Actualizar rankings
    actualizar_rankings()
    
    flash(f'¡Ataque "{ataque.nombre}" comprado exitosamente por {personaje.nombre}!', 'success')
    return redirect(url_for('ver_ataque', ataque_id=ataque_id))

@app.route('/personaje/<int:personaje_id>/ataques')
@login_required
def ataques_personaje(personaje_id):
    """Ver ataques de un personaje específico"""
    personaje = Personaje.query.get_or_404(personaje_id)
    
    # Verificar que el personaje pertenece al usuario
    user = Usuario.query.get(session['user_id'])
    if personaje.creador_id != user.id:
        flash('No puedes ver ataques de personajes que no son tuyos', 'error')
        return redirect(url_for('ataques'))
    
    ataques_personaje = AtaquePersonaje.query.filter_by(personaje_id=personaje.id).all()
    
    return render_template('ataques_personaje.html', personaje=personaje, ataques_personaje=ataques_personaje, user=user)

@app.route('/ataque-personaje/<int:ataque_personaje_id>/vender', methods=['POST'])
@login_required
def vender_ataque(ataque_personaje_id):
    """Vender un ataque (automáticamente al 75% del precio de compra si no es único)"""
    ataque_personaje = AtaquePersonaje.query.get_or_404(ataque_personaje_id)
    
    # Verificar que el personaje pertenece al usuario
    user = Usuario.query.get(session['user_id'])
    if ataque_personaje.personaje.creador_id != user.id:
        flash('No puedes vender ataques de personajes que no son tuyos', 'error')
        return redirect(url_for('ataques_personaje', personaje_id=ataque_personaje.personaje.id))
    
    # Verificar que no está ya en venta
    if ataque_personaje.en_venta:
        flash('Este ataque ya está en venta', 'error')
        return redirect(url_for('ataques_personaje', personaje_id=ataque_personaje.personaje.id))
    
    if ataque_personaje.ataque.es_unico:
        # Para ataques únicos, redirigir a la página de establecer precio
        return redirect(url_for('establecer_precio_ataque', ataque_personaje_id=ataque_personaje_id))
    else:
        # Ataque no único: vender automáticamente al 75% del precio de compra
        precio_venta = int(ataque_personaje.precio_compra * 0.75)
        
        # Acreditar rastamonios al personaje
        ataque_personaje.personaje.rastamonios += precio_venta
        
        # Restaurar stock del ataque si no es ilimitado
        if ataque_personaje.ataque.stock != -1:
            ataque_personaje.ataque.stock += 1
            if not ataque_personaje.ataque.disponible and ataque_personaje.ataque.stock > 0:
                ataque_personaje.ataque.disponible = True
        
        # Eliminar el ataque del personaje
        db.session.delete(ataque_personaje)
        db.session.commit()
        
        # Actualizar rankings
        actualizar_rankings()
        
        flash(f'Ataque "{ataque_personaje.ataque.nombre}" vendido automáticamente por {precio_venta} rastamonios', 'success')
        return redirect(url_for('ataques_personaje', personaje_id=ataque_personaje.personaje.id))

@app.route('/ataque-personaje/<int:ataque_personaje_id>/establecer-precio', methods=['GET', 'POST'])
@login_required
def establecer_precio_ataque(ataque_personaje_id):
    """Establecer precio para vender un ataque único"""
    ataque_personaje = AtaquePersonaje.query.get_or_404(ataque_personaje_id)
    
    # Verificar que el personaje pertenece al usuario
    user = Usuario.query.get(session['user_id'])
    if ataque_personaje.personaje.creador_id != user.id:
        flash('No puedes vender ataques de personajes que no son tuyos', 'error')
        return redirect(url_for('ataques_personaje', personaje_id=ataque_personaje.personaje.id))
    
    # Verificar que es un ataque único
    if not ataque_personaje.ataque.es_unico:
        flash('Esta función solo es para ataques únicos', 'error')
        return redirect(url_for('ataques_personaje', personaje_id=ataque_personaje.personaje.id))
    
    # Verificar que no está ya en venta
    if ataque_personaje.en_venta:
        flash('Este ataque ya está en venta', 'error')
        return redirect(url_for('ataques_personaje', personaje_id=ataque_personaje.personaje.id))
    
    if request.method == 'POST':
        precio_venta = request.form.get('precio_venta')
        
        if not precio_venta or not precio_venta.isdigit():
            flash('Debes ingresar un precio válido', 'error')
            return redirect(url_for('establecer_precio_ataque', ataque_personaje_id=ataque_personaje_id))
        
        precio_venta = int(precio_venta)
        
        if precio_venta <= 0:
            flash('El precio debe ser mayor a 0', 'error')
            return redirect(url_for('establecer_precio_ataque', ataque_personaje_id=ataque_personaje_id))
        
        # Poner en venta con el precio establecido
        ataque_personaje.en_venta = True
        ataque_personaje.precio_venta = precio_venta
        
        # Marcar el ataque como disponible en la tienda nuevamente
        ataque_personaje.ataque.disponible = True
        
        db.session.commit()
        
        # Actualizar rankings (el ataque ya no suma poder)
        actualizar_rankings()
        
        flash(f'Ataque único "{ataque_personaje.ataque.nombre}" puesto en venta por {precio_venta} rastamonios. Recibirás el pago solo si otro usuario lo compra.', 'success')
        return redirect(url_for('ataques_personaje', personaje_id=ataque_personaje.personaje.id))
    
    return render_template('establecer_precio_ataque.html', ataque_personaje=ataque_personaje)

@app.route('/ataque-personaje/<int:ataque_personaje_id>/editar-precio', methods=['GET', 'POST'])
@login_required
def editar_precio_ataque(ataque_personaje_id):
    """Editar precio de un ataque único en venta"""
    ataque_personaje = AtaquePersonaje.query.get_or_404(ataque_personaje_id)
    
    # Verificar que el personaje pertenece al usuario
    user = Usuario.query.get(session['user_id'])
    if ataque_personaje.personaje.creador_id != user.id:
        flash('No puedes editar precios de ataques de personajes que no son tuyos', 'error')
        return redirect(url_for('ataques_personaje', personaje_id=ataque_personaje.personaje.id))
    
    # Verificar que es un ataque único
    if not ataque_personaje.ataque.es_unico:
        flash('Esta función solo es para ataques únicos', 'error')
        return redirect(url_for('ataques_personaje', personaje_id=ataque_personaje.personaje.id))
    
    # Verificar que está en venta
    if not ataque_personaje.en_venta:
        flash('Este ataque no está en venta', 'error')
        return redirect(url_for('ataques_personaje', personaje_id=ataque_personaje.personaje.id))
    
    if request.method == 'POST':
        precio_venta = request.form.get('precio_venta')
        
        if not precio_venta or not precio_venta.isdigit():
            flash('Debes ingresar un precio válido', 'error')
            return redirect(url_for('editar_precio_ataque', ataque_personaje_id=ataque_personaje_id))
        
        precio_venta = int(precio_venta)
        
        if precio_venta <= 0:
            flash('El precio debe ser mayor a 0', 'error')
            return redirect(url_for('editar_precio_ataque', ataque_personaje_id=ataque_personaje_id))
        
        # Actualizar el precio de venta
        ataque_personaje.precio_venta = precio_venta
        db.session.commit()
        
        flash(f'Precio del ataque único "{ataque_personaje.ataque.nombre}" actualizado a {precio_venta} rastamonios', 'success')
        return redirect(url_for('ataques_personaje', personaje_id=ataque_personaje.personaje.id))
    
    return render_template('editar_precio_ataque.html', ataque_personaje=ataque_personaje)

@app.route('/ataque-personaje/<int:ataque_personaje_id>/cancelar-venta', methods=['POST'])
@login_required
def cancelar_venta_ataque(ataque_personaje_id):
    """Cancelar la venta de un ataque"""
    ataque_personaje = AtaquePersonaje.query.get_or_404(ataque_personaje_id)
    
    # Verificar que el personaje pertenece al usuario
    user = Usuario.query.get(session['user_id'])
    if ataque_personaje.personaje.creador_id != user.id:
        flash('No puedes cancelar ventas de ataques de personajes que no son tuyos', 'error')
        return redirect(url_for('ataques_personaje', personaje_id=ataque_personaje.personaje.id))
    
    # Verificar que está en venta
    if not ataque_personaje.en_venta:
        flash('Este ataque no está en venta', 'error')
        return redirect(url_for('ataques_personaje', personaje_id=ataque_personaje.personaje.id))
    
    # Cancelar venta
    ataque_personaje.en_venta = False
    ataque_personaje.precio_venta = None
    
    # Si es un ataque único, marcarlo como no disponible en la tienda
    if ataque_personaje.ataque.es_unico:
        ataque_personaje.ataque.disponible = False
    
    db.session.commit()
    
    # Actualizar rankings (el ataque vuelve a sumar poder)
    actualizar_rankings()
    
    flash(f'Venta del ataque "{ataque_personaje.ataque.nombre}" cancelada', 'success')
    return redirect(url_for('ataques_personaje', personaje_id=ataque_personaje.personaje.id))

@app.route('/ataques/venta')
@login_required
def ataques_en_venta():
    """Ver ataques en venta de otros usuarios"""
    ataques_en_venta = AtaquePersonaje.query.filter_by(en_venta=True).all()
    user = Usuario.query.get(session['user_id'])
    personajes = Personaje.query.filter_by(creador_id=user.id).all()
    
    return render_template('ataques_en_venta.html', ataques_en_venta=ataques_en_venta, personajes=personajes, user=user)

@app.route('/ataque-personaje/<int:ataque_personaje_id>/comprar/<int:personaje_id>', methods=['POST'])
@login_required
def comprar_ataque_en_venta(ataque_personaje_id, personaje_id):
    """Comprar un ataque que está en venta"""
    ataque_personaje = AtaquePersonaje.query.get_or_404(ataque_personaje_id)
    personaje_comprador = Personaje.query.get_or_404(personaje_id)
    
    # Verificar que el personaje pertenece al usuario
    user = Usuario.query.get(session['user_id'])
    if personaje_comprador.creador_id != user.id:
        flash('No puedes comprar ataques para personajes que no son tuyos', 'error')
        return redirect(url_for('ataques_en_venta'))
    
    # Verificar que está en venta
    if not ataque_personaje.en_venta:
        flash('Este ataque no está en venta', 'error')
        return redirect(url_for('ataques_en_venta'))
    
    # Verificar que no es el mismo personaje
    if ataque_personaje.personaje_id == personaje_comprador.id:
        flash('No puedes comprar tu propio ataque', 'error')
        return redirect(url_for('ataques_en_venta'))
    
    # Verificar que el comprador tiene suficientes rastamonios
    if personaje_comprador.rastamonios < ataque_personaje.precio_venta:
        flash('No tienes suficientes rastamonios para comprar este ataque', 'error')
        return redirect(url_for('ataques_en_venta'))
    
    # Verificar límite de 50 ataques por personaje
    ataques_actuales = AtaquePersonaje.query.filter_by(personaje_id=personaje_comprador.id).count()
    if ataques_actuales >= 50:
        flash('Este personaje ya tiene el límite máximo de 50 ataques', 'error')
        return redirect(url_for('ataques_en_venta'))
    
    # Realizar la transacción
    personaje_comprador.rastamonios -= ataque_personaje.precio_venta
    ataque_personaje.personaje.rastamonios += ataque_personaje.precio_venta
    
    # Transferir el ataque
    ataque_personaje.personaje_id = personaje_comprador.id
    ataque_personaje.en_venta = False
    ataque_personaje.precio_venta = None
    
    # Si es un ataque único, marcarlo como no disponible en la tienda
    if ataque_personaje.ataque.es_unico:
        ataque_personaje.ataque.disponible = False
    
    db.session.commit()
    
    # Actualizar rankings
    actualizar_rankings()
    
    flash(f'¡Ataque "{ataque_personaje.ataque.nombre}" comprado exitosamente por {personaje_comprador.nombre}!', 'success')
    return redirect(url_for('ataques_en_venta'))

# ===== ADMINISTRACIÓN DE ATAQUES =====

@app.route('/admin/ataques')
@admin_required
def admin_ataques():
    """Administrar ataques disponibles"""
    ataques = Ataque.query.all()
    return render_template('admin_ataques.html', ataques=ataques)

@app.route('/admin/ataque/nuevo', methods=['GET', 'POST'])
@admin_required
def nuevo_ataque():
    """Crear nuevo ataque"""
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        descripcion = request.form.get('descripcion')
        poder = int(request.form.get('poder'))
        precio = int(request.form.get('precio'))
        stock = int(request.form.get('stock'))
        es_unico = request.form.get('es_unico') == 'on'  # Checkbox marcado = True
        clan_requerido = request.form.get('clan_requerido')
        if clan_requerido == '':
            clan_requerido = None
        else:
            clan_requerido = int(clan_requerido)
        
        # Manejar subida de imagen (opcional)
        imagen_path = None
        if 'imagen' in request.files:
            file = request.files['imagen']
            if file.filename != '':
                if not allowed_file(file.filename):
                    flash('Formato de archivo no permitido. Use: PNG, JPG, JPEG, GIF, WEBP', 'error')
                    return redirect(request.url)
                
                filename = secure_filename(f"ataque_{nombre}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{file.filename.rsplit('.', 1)[1].lower()}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                imagen_path = f'uploads/{filename}'
        
        nuevo_ataque = Ataque(
            nombre=nombre,
            descripcion=descripcion,
            imagen=imagen_path,
            poder=poder,
            precio=precio,
            stock=stock,
            es_unico=es_unico,
            clan_requerido=clan_requerido
        )
        
        db.session.add(nuevo_ataque)
        db.session.commit()
        
        flash('Ataque creado exitosamente', 'success')
        return redirect(url_for('admin_ataques'))
    
    # Obtener clanes disponibles para el formulario
    clanes = Clan.query.filter_by(activo=True).order_by(Clan.nombre).all()
    return render_template('nuevo_ataque.html', clanes=clanes)

@app.route('/admin/ataque/<int:ataque_id>/editar', methods=['GET', 'POST'])
@admin_required
def editar_ataque(ataque_id):
    """Editar ataque existente"""
    ataque = Ataque.query.get_or_404(ataque_id)
    
    if request.method == 'POST':
        ataque.nombre = request.form.get('nombre')
        ataque.descripcion = request.form.get('descripcion')
        ataque.poder = int(request.form.get('poder'))
        ataque.precio = int(request.form.get('precio'))
        ataque.stock = int(request.form.get('stock'))
        ataque.es_unico = request.form.get('es_unico') == 'on'  # Checkbox marcado = True
        clan_requerido = request.form.get('clan_requerido')
        if clan_requerido == '':
            ataque.clan_requerido = None
        else:
            ataque.clan_requerido = int(clan_requerido)
        
        # Manejar nueva imagen (opcional)
        if 'imagen' in request.files:
            file = request.files['imagen']
            if file.filename != '':
                if not allowed_file(file.filename):
                    flash('Formato de archivo no permitido. Use: PNG, JPG, JPEG, GIF, WEBP', 'error')
                    return redirect(request.url)
                
                filename = secure_filename(f"ataque_{ataque.nombre}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{file.filename.rsplit('.', 1)[1].lower()}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                ataque.imagen = f'uploads/{filename}'
        
        db.session.commit()
        
        flash('Ataque actualizado exitosamente', 'success')
        return redirect(url_for('admin_ataques'))
    
    # Obtener clanes disponibles para el formulario
    clanes = Clan.query.filter_by(activo=True).order_by(Clan.nombre).all()
    return render_template('editar_ataque.html', ataque=ataque, clanes=clanes)

@app.route('/admin/ataque/<int:ataque_id>/toggle', methods=['POST'])
@admin_required
def toggle_ataque(ataque_id):
    """Activar/desactivar ataque"""
    ataque = Ataque.query.get_or_404(ataque_id)
    ataque.disponible = not ataque.disponible
    
    db.session.commit()
    
    estado = "activado" if ataque.disponible else "desactivado"
    flash(f'Ataque {estado} exitosamente', 'success')
    return redirect(url_for('admin_ataques'))

@app.route('/admin/ataque/<int:ataque_id>/eliminar', methods=['POST'])
@admin_required
def eliminar_ataque(ataque_id):
    """Eliminar ataque"""
    ataque = Ataque.query.get_or_404(ataque_id)
    
    # Verificar que no hay personajes que tengan este ataque
    ataques_personaje = AtaquePersonaje.query.filter_by(ataque_id=ataque_id).count()
    if ataques_personaje > 0:
        flash('No se puede eliminar un ataque que ya ha sido comprado por personajes', 'error')
        return redirect(url_for('admin_ataques'))
    
    db.session.delete(ataque)
    db.session.commit()
    
    flash('Ataque eliminado exitosamente', 'success')
    return redirect(url_for('admin_ataques'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 