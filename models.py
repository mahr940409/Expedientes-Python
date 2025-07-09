from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

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
    personaje_id = db.Column(db.Integer, db.ForeignKey('personaje.id'), nullable=False)

class Elemento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False, unique=True)
    descripcion = db.Column(db.Text)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)  # Opcional
    password_hash = db.Column(db.String(255), nullable=False)
    es_admin = db.Column(db.Boolean, default=False)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    personajes_creados = db.relationship('Personaje', backref='creador', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def puede_crear_personaje(self):
        if self.es_admin:
            return True
        from models import db
        count = db.session.query(Personaje).filter_by(creador_id=self.id).count()
        return count < 3 