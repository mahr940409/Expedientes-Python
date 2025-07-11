from app import app, db
from models import Elemento, Usuario

def init_elementos():
    with app.app_context():
        db.drop_all()
        db.create_all()

        # Elementos básicos
        elementos_basicos = [
            {'nombre': 'Fuego', 'descripcion': 'Control del fuego, llamas y calor.', 'es_basico': True},
            {'nombre': 'Agua', 'descripcion': 'Manipulación del agua y fluidos.', 'es_basico': True},
            {'nombre': 'Aire', 'descripcion': 'Control del viento y tormentas.', 'es_basico': True},
            {'nombre': 'Tierra', 'descripcion': 'Control de rocas, minerales y terremotos.', 'es_basico': True},
        ]
        # Elementos avanzados
        elementos_avanzados = [
            {'nombre': 'Electricidad', 'descripcion': 'Control de rayos y energía eléctrica.', 'es_basico': False},
            {'nombre': 'Hielo', 'descripcion': 'Control del hielo y temperaturas bajas.', 'es_basico': False},
            {'nombre': 'Veneno', 'descripcion': 'Control de sustancias tóxicas y venenos.', 'es_basico': False},
            {'nombre': 'Luz', 'descripcion': 'Manipulación de la luz y energía sagrada.', 'es_basico': False},
            {'nombre': 'Oscuridad', 'descripcion': 'Control de sombras y energía oscura.', 'es_basico': False},
            {'nombre': 'Rastamonio', 'descripcion': 'Elemento legendario que combina múltiples fuerzas.', 'es_basico': False},
        ]
        for elem in elementos_basicos + elementos_avanzados:
            db.session.add(Elemento(**elem))
        db.session.commit()
        print('Elementos creados correctamente.')

        # Crear usuarios de ejemplo
        admin = Usuario(username='Burs', email='burs@admin.com', es_admin=True)
        admin.set_password('Hinata9404')
        db.session.add(admin)
        user = Usuario(username='usuario_normal', email='usuario@ejemplo.com', es_admin=False)
        user.set_password('Hinata9404')
        db.session.add(user)
        db.session.commit()
        print('Usuarios de ejemplo creados correctamente.')

if __name__ == '__main__':
    init_elementos()
    print('¡Base de datos inicializada!') 