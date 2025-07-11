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

class Personaje(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    dimension = db.Column(db.String(50), nullable=False)
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
    compras = db.relationship('Compra', backref='personaje_compra', cascade='all, delete-orphan')
    rastamonios = db.Column(db.Integer, default=10000, nullable=False)

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
        for arma in self.armas:
            poder_arma = niveles_poder.get(arma.nivel, 0)
            poder_base += poder_arma * 0.5  # Las armas suman 50% de su poder
        
        # Poder por invocaciones
        for invocacion in self.invocaciones:
            poder_invocacion = niveles_poder.get(invocacion.nivel, 0)
            poder_base += poder_invocacion * 0.8  # Las invocaciones suman 80% de su poder
        
        # Bonus por elementos (más elementos = más poder)
        if self.elementos:
            elementos_lista = json.loads(self.elementos) if isinstance(self.elementos, str) else self.elementos
            bonus_elementos = len(elementos_lista) * 50
            poder_base += bonus_elementos
        
        # Poder adicional por items comprados en la tienda
        for compra in self.compras:
            if compra.item and compra.item.poder_adicional:
                poder_base += compra.item.poder_adicional * compra.cantidad
        
        return int(poder_base)

    @property
    def poder_total(self):
        """Propiedad para obtener el poder total"""
        return self.calcular_poder()

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
    rango = db.Column(db.String(100), nullable=False)
    nivel = db.Column(db.String(2), nullable=False)
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
    rango = db.Column(db.String(100), nullable=False)
    nivel = db.Column(db.String(2), nullable=False)
    estado = db.Column(db.String(20), default='pendiente')  # pendiente, aprobada, rechazada
    motivo = db.Column(db.Text)  # Motivo de la solicitud
    respuesta_admin = db.Column(db.Text)  # Respuesta del administrador
    fecha_solicitud = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_respuesta = db.Column(db.DateTime)
    
    usuario = db.relationship('Usuario', backref='solicitudes_invocaciones')
    personaje = db.relationship('Personaje')

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

class Compra(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    personaje_id = db.Column(db.Integer, db.ForeignKey('personaje.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('tienda_item.id'), nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    cantidad = db.Column(db.Integer, default=1)
    personaje = db.relationship('Personaje')
    item = db.relationship('TiendaItem')

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