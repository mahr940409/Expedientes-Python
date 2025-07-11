from app import app, db
from models import TiendaItem, Personaje

def init_tienda():
    with app.app_context():
        # Verificar si ya existen items en la tienda
        items_existentes = TiendaItem.query.count()
        if items_existentes > 0:
            print(f'Ya existen {items_existentes} items en la tienda.')
            return

        # Items de la tienda
        items_tienda = [
            {
                'nombre': 'Poción de Curación',
                'descripcion': 'Restaura la salud del personaje completamente. Útil en batallas largas.',
                'precio': 500,
                'imagen': 'uploads/pocion_curacion.jpg',
                'disponible': True
            },
            {
                'nombre': 'Elixir de Poder',
                'descripcion': 'Aumenta temporalmente el poder del personaje en un 50% durante 1 hora.',
                'precio': 1000,
                'imagen': 'uploads/elixir_poder.jpg',
                'disponible': True
            },
            {
                'nombre': 'Escudo Mágico',
                'descripcion': 'Protege al personaje de ataques mágicos. Duración: 30 minutos.',
                'precio': 750,
                'imagen': 'uploads/escudo_magico.jpg',
                'disponible': True
            },
            {
                'nombre': 'Piedra de Teletransporte',
                'descripcion': 'Permite al personaje teletransportarse a cualquier planeta conocido.',
                'precio': 2000,
                'imagen': 'uploads/piedra_teleport.jpg',
                'disponible': True
            },
            {
                'nombre': 'Amuleto de Protección',
                'descripcion': 'Reduce el daño recibido en un 25%. Efecto permanente hasta que se destruya.',
                'precio': 3000,
                'imagen': 'uploads/amuleto_proteccion.jpg',
                'disponible': True
            },
            {
                'nombre': 'Espada Legendaria',
                'descripcion': 'Una espada mágica que aumenta el poder de ataque del personaje.',
                'precio': 5000,
                'imagen': 'uploads/espada_legendaria.jpg',
                'disponible': True
            },
            {
                'nombre': 'Grimorio de Hechizos',
                'descripcion': 'Contiene hechizos poderosos que pueden ser aprendidos por el personaje.',
                'precio': 4000,
                'imagen': 'uploads/grimorio_hechizos.jpg',
                'disponible': True
            },
            {
                'nombre': 'Cristal de Energía',
                'descripcion': 'Recarga completamente la energía mágica del personaje.',
                'precio': 800,
                'imagen': 'uploads/cristal_energia.jpg',
                'disponible': True
            }
        ]

        # Crear items en la base de datos
        for item_data in items_tienda:
            nuevo_item = TiendaItem(**item_data)
            db.session.add(nuevo_item)
        
        db.session.commit()
        print(f'Se crearon {len(items_tienda)} items en la tienda.')

def asignar_rastamonios_iniciales():
    """Asignar rastamonios iniciales a todos los personajes"""
    with app.app_context():
        personajes = Personaje.query.all()
        for personaje in personajes:
            if personaje.rastamonios == 0 or personaje.rastamonios is None:
                personaje.rastamonios = 10000
                print(f'Asignados 10000 rastamonios a {personaje.nombre}')
        
        db.session.commit()
        print(f'Se actualizaron {len(personajes)} personajes con rastamonios iniciales.')

if __name__ == '__main__':
    print('Inicializando tienda...')
    init_tienda()
    print('Asignando rastamonios iniciales...')
    asignar_rastamonios_iniciales()
    print('¡Tienda inicializada correctamente!') 