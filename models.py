from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import json

db = SQLAlchemy()

class Planeta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False, unique=True)
    dimension = db.Column(db.String(50), nullable=False)
    descripcion = db.Column(db.Text)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    es_publico = db.Column(db.Boolean, default=True, nullable=False)  # True = público, False = restringido
    duenio_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=True)  # Dueño del planeta
    duenio = db.relationship('Usuario', backref='planetas_propios', foreign_keys=[duenio_id])

class Personaje(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    dimension = db.Column(db.String(50), nullable=True)
    planeta = db.Column(db.String(100))
    edad = db.Column(db.Integer, nullable=False)
    rango = db.Column(db.String(100), nullable=False)
    nivel = db.Column(db.String(2), nullable=False)
    foto = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    elementos = db.Column(db.Text)  # Almacenado como JSON string
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    creador_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=True)
    armas = db.relationship('Arma', backref='personaje', cascade='all, delete-orphan')
    invocaciones = db.relationship('Invocacion', backref='personaje', cascade='all, delete-orphan')
    compras = db.relationship('Compra', backref='personaje_compra', cascade='all, delete-orphan', foreign_keys='Compra.personaje_id')
    rastamonios = db.Column(db.Integer, default=10000, nullable=False)
    poder_misiones = db.Column(db.Integer, default=0, nullable=False)  # Poder ganado por misiones
    poder_regalado = db.Column(db.Integer, default=0, nullable=False)  # Poder regalado por administradores (oculto)
    clan_id = db.Column(db.Integer, db.ForeignKey('clan.id'), nullable=True)  # Clan al que pertenece

    def calcular_poder(self):
        """Calcula el poder total del personaje"""
        poder_base = 0
        
        # Poder por nivel del personaje
        niveles_poder = {
            'D': 100, 'C': 250, 'B': 500, 
            'A': 1000, 'S': 2000
        }
        poder_base += niveles_poder.get(self.nivel, 0)
        
        # Poder por armas
        for arma in self.armas_nuevas:
            poder_base += arma.poder  # Las armas suman su poder directamente
        
        # Poder por invocaciones
        for invocacion in self.invocaciones_nuevas:
            poder_base += invocacion.poder  # Las invocaciones suman su poder directamente
        
        # Bonus por elementos (más elementos = más poder)
        if self.elementos:
            elementos_lista = json.loads(self.elementos) if isinstance(self.elementos, str) else self.elementos
            bonus_elementos = len(elementos_lista) * 50
            poder_base += bonus_elementos
        
        # Poder adicional por items comprados en la tienda
        for compra in self.compras:
            if compra.item and compra.item.poder_adicional:
                poder_base += compra.item.poder_adicional * compra.cantidad
        
        # Poder ganado por misiones
        poder_base += self.poder_misiones or 0
        
        # Poder regalado por administradores (oculto)
        poder_base += self.poder_regalado or 0
        
        # Poder de ataques comprados (solo los que no están en venta)
        for ataque_personaje in self.ataques_comprados:
            if not ataque_personaje.en_venta:
                poder_base += ataque_personaje.ataque.poder
        
        return int(poder_base)

    @property
    def poder_total(self):
        """Propiedad para obtener el poder total"""
        return self.calcular_poder()

    @property
    def nivel_auto(self):
        poder = self.calcular_poder()
        if poder < 60000:
            return 'D'
        elif poder < 130000:
            return 'C'
        elif poder < 210000:
            return 'B'
        elif poder < 300000:
            return 'A'
        else:
            return 'S'

    @property
    def siguiente_nivel_info(self):
        poder = self.calcular_poder()
        niveles = [
            ('D', 0, 60000),
            ('C', 60000, 130000),
            ('B', 130000, 210000),
            ('A', 210000, 300000),
            ('S', 300000, float('inf'))
        ]
        for idx, (nivel, min_p, max_p) in enumerate(niveles):
            if min_p <= poder < max_p:
                falta = max_p - poder
                siguiente = niveles[idx+1][0] if idx+1 < len(niveles) else 'S'
                progreso = int(100 * (poder - min_p) / (max_p - min_p)) if max_p != float('inf') else 100
                return {
                    'nivel_actual': nivel,
                    'nivel_siguiente': siguiente,
                    'falta': falta,
                    'progreso': progreso,
                    'min_p': min_p,
                    'max_p': max_p
                }
        # Si ya es S
        return {
            'nivel_actual': 'S',
            'nivel_siguiente': None,
            'falta': 0,
            'progreso': 100,
            'min_p': 300000,
            'max_p': 300000
        }

class Ranking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    personaje_id = db.Column(db.Integer, db.ForeignKey('personaje.id', ondelete='CASCADE'), nullable=False)
    poder_total = db.Column(db.Integer, nullable=False)
    posicion = db.Column(db.Integer, nullable=False)
    fecha_actualizacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    personaje = db.relationship('Personaje', backref='rankings')

class Arma(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    imagen = db.Column(db.String(200), nullable=False)
    rango = db.Column(db.String(100), nullable=False)
    nivel = db.Column(db.String(2), nullable=False)
    personaje_id = db.Column(db.Integer, db.ForeignKey('personaje.id'), nullable=False)

class Invocacion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    imagen = db.Column(db.String(200), nullable=False)
    poder = db.Column(db.Integer, nullable=False)  # Poder que suma al personaje
    personaje_id = db.Column(db.Integer, db.ForeignKey('personaje.id'), nullable=False)

class Elemento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False, unique=True)
    descripcion = db.Column(db.Text)
    es_basico = db.Column(db.Boolean, default=True)  # True = básico, False = avanzado
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

class SolicitudElemento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    elemento_id = db.Column(db.Integer, db.ForeignKey('elemento.id'), nullable=False)
    personaje_id = db.Column(db.Integer, db.ForeignKey('personaje.id'), nullable=False)
    estado = db.Column(db.String(20), default='pendiente')  # pendiente, aprobada, rechazada
    motivo = db.Column(db.Text)  # Motivo de la solicitud
    respuesta_admin = db.Column(db.Text)  # Respuesta del administrador
    fecha_solicitud = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_respuesta = db.Column(db.DateTime)
    
    usuario = db.relationship('Usuario', backref='solicitudes_elementos')
    elemento = db.relationship('Elemento')
    personaje = db.relationship('Personaje')

class SolicitudArma(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    personaje_id = db.Column(db.Integer, db.ForeignKey('personaje.id'), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    imagen = db.Column(db.String(200), nullable=False)
    rango = db.Column(db.String(100), nullable=False)
    nivel = db.Column(db.String(2), nullable=False)
    estado = db.Column(db.String(20), default='pendiente')  # pendiente, aprobada, rechazada
    motivo = db.Column(db.Text)  # Motivo de la solicitud
    respuesta_admin = db.Column(db.Text)  # Respuesta del administrador
    fecha_solicitud = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_respuesta = db.Column(db.DateTime)
    
    usuario = db.relationship('Usuario', backref='solicitudes_armas')
    personaje = db.relationship('Personaje')

class SolicitudInvocacion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    personaje_id = db.Column(db.Integer, db.ForeignKey('personaje.id'), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    imagen = db.Column(db.String(200), nullable=False)
    poder = db.Column(db.Integer, nullable=False)  # Poder que suma al personaje
    estado = db.Column(db.String(20), default='pendiente')  # pendiente, aprobada, rechazada
    motivo = db.Column(db.Text)  # Motivo de la solicitud
    respuesta_admin = db.Column(db.Text)  # Respuesta del administrador
    fecha_solicitud = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_respuesta = db.Column(db.DateTime)
    
    usuario = db.relationship('Usuario', backref='solicitudes_invocaciones')
    personaje = db.relationship('Personaje')

class SolicitudPlaneta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    personaje_id = db.Column(db.Integer, db.ForeignKey('personaje.id'), nullable=False)
    planeta_id = db.Column(db.Integer, db.ForeignKey('planeta.id'), nullable=False)
    estado = db.Column(db.String(20), default='pendiente')  # pendiente, aceptada, rechazada, cancelada
    fecha_solicitud = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_respuesta = db.Column(db.DateTime)
    
    personaje = db.relationship('Personaje')
    planeta = db.relationship('Planeta')

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)  # Opcional
    password_hash = db.Column(db.String(255), nullable=False)
    es_admin = db.Column(db.Boolean, default=False)
    nivel_usuario = db.Column(db.String(20), default='normal')  # normal, premium, vip, legendario
    slots_comprados = db.Column(db.Integer, default=0)  # Slots adicionales comprados
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    personajes_creados = db.relationship('Personaje', backref='creador', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def puede_crear_personaje(self):
        if self.es_admin:
            return True
        
        # Límites por nivel de usuario + slots comprados
        limites = {
            'normal': 3,
            'premium': 5,
            'vip': 8,
            'legendario': 12
        }
        
        limite_base = limites.get(self.nivel_usuario, 3)
        limite_total = limite_base + self.slots_comprados
        
        from models import db
        count = db.session.query(Personaje).filter_by(creador_id=self.id).count()
        return count < limite_total
    
    def obtener_limite_personajes(self):
        """Obtiene el límite de personajes según el nivel del usuario + slots comprados"""
        if self.es_admin:
            return 999  # Los administradores pueden crear muchos personajes
        
        limites = {
            'normal': 3,
            'premium': 5,
            'vip': 8,
            'legendario': 12
        }
        
        limite_base = limites.get(self.nivel_usuario, 3)
        return limite_base + self.slots_comprados
    
    def obtener_precio_siguiente_slot(self):
        """Obtiene el precio del siguiente slot de personaje"""
        # Precio base: 50000 rastamonios, aumenta 10000 por cada slot comprado
        return 50000 + (self.slots_comprados * 10000)

class TiendaItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    precio = db.Column(db.Integer, nullable=False)
    imagen = db.Column(db.String(200), nullable=True)
    disponible = db.Column(db.Boolean, default=True)
    es_unico = db.Column(db.Boolean, default=False)  # True = item único, False = múltiples disponibles
    stock = db.Column(db.Integer, default=-1)  # -1 = stock ilimitado, >= 0 = cantidad disponible
    poder_adicional = db.Column(db.Integer, default=0)  # Poder que suma al personaje
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relación con las compras de este ítem
    compras = db.relationship('Compra', backref='item_compra', cascade='all, delete-orphan')

class Compra(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    personaje_id = db.Column(db.Integer, db.ForeignKey('personaje.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('tienda_item.id'), nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    cantidad = db.Column(db.Integer, default=1)
    personaje = db.relationship('Personaje', foreign_keys=[personaje_id])
    item = db.relationship('TiendaItem')
    # Nuevos campos para venta de ítems únicos
    en_venta = db.Column(db.Boolean, default=False)  # True si está en venta
    precio_venta = db.Column(db.Integer, nullable=True)  # Precio de venta si está en venta
    vendedor_id = db.Column(db.Integer, db.ForeignKey('personaje.id'), nullable=True)  # Personaje que vende el ítem único
    vendedor = db.relationship('Personaje', foreign_keys=[vendedor_id], backref='ventas_realizadas')

class Mensaje(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    remitente_id = db.Column(db.Integer, db.ForeignKey('personaje.id'), nullable=False)
    destinatario_id = db.Column(db.Integer, db.ForeignKey('personaje.id'), nullable=False)
    asunto = db.Column(db.String(200), nullable=False)
    contenido = db.Column(db.Text, nullable=False)
    fecha_envio = db.Column(db.DateTime, default=datetime.utcnow)
    leido = db.Column(db.Boolean, default=False)
    
    # Relaciones
    remitente = db.relationship('Personaje', foreign_keys=[remitente_id], backref='mensajes_enviados')
    destinatario = db.relationship('Personaje', foreign_keys=[destinatario_id], backref='mensajes_recibidos')

class Mision(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    imagen = db.Column(db.String(200), nullable=True)  # Campo para la imagen de la misión
    poder_minimo = db.Column(db.Integer, nullable=False)
    recompensa_poder = db.Column(db.Integer, nullable=False)
    recompensa_rastamonios = db.Column(db.Integer, nullable=False)
    duracion_segundos = db.Column(db.Integer, nullable=False)  # Duración en segundos
    activa = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

class MisionPersonaje(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    personaje_id = db.Column(db.Integer, db.ForeignKey('personaje.id'), nullable=False)
    mision_id = db.Column(db.Integer, db.ForeignKey('mision.id'), nullable=False)
    estado = db.Column(db.String(20), default='en_progreso')  # en_progreso, completada, fallida, expirada
    fecha_inicio = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_completada = db.Column(db.DateTime)
    fecha_expiracion = db.Column(db.DateTime)  # Cuándo expira la misión
    
    personaje = db.relationship('Personaje', backref='misiones_activas')
    mision = db.relationship('Mision')

class Ataque(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    imagen = db.Column(db.String(200), nullable=True)
    poder = db.Column(db.Integer, nullable=False)  # Poder que suma al personaje
    precio = db.Column(db.Integer, nullable=False)  # Precio en rastamonios
    disponible = db.Column(db.Boolean, default=True)
    stock = db.Column(db.Integer, default=-1)  # -1 = stock ilimitado, >= 0 = cantidad disponible
    es_unico = db.Column(db.Boolean, default=False)  # True = ataque único, False = múltiples disponibles
    clan_requerido = db.Column(db.Integer, db.ForeignKey('clan.id'), nullable=True)  # Clan requerido para comprar este ataque
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

class AtaquePersonaje(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    personaje_id = db.Column(db.Integer, db.ForeignKey('personaje.id'), nullable=False)
    ataque_id = db.Column(db.Integer, db.ForeignKey('ataque.id'), nullable=False)
    precio_compra = db.Column(db.Integer, nullable=False)  # Precio al que se compró
    fecha_compra = db.Column(db.DateTime, default=datetime.utcnow)
    en_venta = db.Column(db.Boolean, default=False)  # True si está en venta
    precio_venta = db.Column(db.Integer, nullable=True)  # Precio de venta (75% del precio de compra)
    
    personaje = db.relationship('Personaje', backref='ataques_comprados')
    ataque = db.relationship('Ataque') 

class ArmaNueva(db.Model):
    __tablename__ = 'arma_nueva'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    imagen = db.Column(db.String(200), nullable=False)
    poder = db.Column(db.Integer, nullable=False)
    personaje_id = db.Column(db.Integer, db.ForeignKey('personaje.id'), nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    personaje = db.relationship('Personaje', backref='armas_nuevas')

class SolicitudArmaNueva(db.Model):
    __tablename__ = 'solicitud_arma_nueva'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    personaje_id = db.Column(db.Integer, db.ForeignKey('personaje.id'), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    imagen = db.Column(db.String(200), nullable=False)
    poder = db.Column(db.Integer, nullable=False)
    estado = db.Column(db.String(20), default='pendiente')
    motivo = db.Column(db.Text)
    respuesta_admin = db.Column(db.Text)
    fecha_solicitud = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_respuesta = db.Column(db.DateTime)

    usuario = db.relationship('Usuario', backref='solicitudes_armas_nuevas')
    personaje = db.relationship('Personaje')

class InvocacionNueva(db.Model):
    __tablename__ = 'invocacion_nueva'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    imagen = db.Column(db.String(200), nullable=False)
    poder = db.Column(db.Integer, nullable=False)
    personaje_id = db.Column(db.Integer, db.ForeignKey('personaje.id'), nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    personaje = db.relationship('Personaje', backref='invocaciones_nuevas')

class SolicitudInvocacionNueva(db.Model):
    __tablename__ = 'solicitud_invocacion_nueva'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    personaje_id = db.Column(db.Integer, db.ForeignKey('personaje.id'), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    imagen = db.Column(db.String(200), nullable=False)
    poder = db.Column(db.Integer, nullable=False)
    estado = db.Column(db.String(20), default='pendiente')
    motivo = db.Column(db.Text)
    respuesta_admin = db.Column(db.Text)
    fecha_solicitud = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_respuesta = db.Column(db.DateTime)

    usuario = db.relationship('Usuario', backref='solicitudes_invocaciones_nuevas')
    personaje = db.relationship('Personaje')

# ===== SISTEMA DE CLANES =====

class Clan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False, unique=True)
    descripcion = db.Column(db.Text, nullable=True)
    insignia = db.Column(db.String(200), nullable=True)  # Ruta de la imagen de la insignia
    creador_id = db.Column(db.Integer, db.ForeignKey('personaje.id'), nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    activo = db.Column(db.Boolean, default=True)
    
    # Relaciones
    creador = db.relationship('Personaje', foreign_keys=[creador_id], backref='clan_creado')
    miembros = db.relationship('Personaje', foreign_keys='Personaje.clan_id', backref='clan')
    solicitudes = db.relationship('SolicitudClan', backref='clan', cascade='all, delete-orphan')
    ataques_exclusivos = db.relationship('Ataque', foreign_keys='Ataque.clan_requerido', backref='clan_exclusivo')

class SolicitudClan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    personaje_id = db.Column(db.Integer, db.ForeignKey('personaje.id'), nullable=False)
    clan_id = db.Column(db.Integer, db.ForeignKey('clan.id'), nullable=False)
    estado = db.Column(db.String(20), default='pendiente')  # pendiente, aceptada, rechazada
    mensaje = db.Column(db.Text, nullable=True)  # Mensaje de la solicitud
    fecha_solicitud = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_respuesta = db.Column(db.DateTime, nullable=True)
    
    # Relaciones
    personaje = db.relationship('Personaje', backref='solicitudes_clan')

class MiembroClan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    personaje_id = db.Column(db.Integer, db.ForeignKey('personaje.id'), nullable=False)
    clan_id = db.Column(db.Integer, db.ForeignKey('clan.id'), nullable=False)
    jerarquia = db.Column(db.String(20), default='miembro')  # lider, colider, elite, miembro
    fecha_ingreso = db.Column(db.DateTime, default=datetime.utcnow)
    asignado_por = db.Column(db.Integer, db.ForeignKey('personaje.id'), nullable=True)  # Quién asignó la jerarquía
    
    # Relaciones
    personaje = db.relationship('Personaje', foreign_keys=[personaje_id], backref='membresia_clan')
    clan = db.relationship('Clan', backref='membresias')
    asignador = db.relationship('Personaje', foreign_keys=[asignado_por]) 