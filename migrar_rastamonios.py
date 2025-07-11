import sqlite3
import os

def migrar_rastamonios():
    """Migrar la base de datos para agregar la columna rastamonios"""
    
    # Ruta de la base de datos
    db_path = 'instance/expedientes.db'
    
    if not os.path.exists(db_path):
        print('Base de datos no encontrada. Creando nueva base de datos...')
        return
    
    try:
        # Conectar a la base de datos
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar si la columna rastamonios ya existe
        cursor.execute("PRAGMA table_info(personaje)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'rastamonios' not in columns:
            print('Agregando columna rastamonios a la tabla personaje...')
            
            # Agregar la columna rastamonios
            cursor.execute("ALTER TABLE personaje ADD COLUMN rastamonios INTEGER DEFAULT 10000")
            
            # Actualizar todos los personajes existentes con 10000 rastamonios
            cursor.execute("UPDATE personaje SET rastamonios = 10000 WHERE rastamonios IS NULL")
            
            conn.commit()
            print('Columna rastamonios agregada exitosamente.')
        else:
            print('La columna rastamonios ya existe.')
        
        # Verificar si la tabla tienda_item existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tienda_item'")
        if not cursor.fetchone():
            print('Creando tabla tienda_item...')
            cursor.execute("""
                CREATE TABLE tienda_item (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre VARCHAR(100) NOT NULL,
                    descripcion TEXT,
                    precio INTEGER NOT NULL,
                    imagen VARCHAR(200),
                    disponible BOOLEAN DEFAULT 1
                )
            """)
            
            # Crear tabla compra
            cursor.execute("""
                CREATE TABLE compra (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    personaje_id INTEGER NOT NULL,
                    item_id INTEGER NOT NULL,
                    fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
                    cantidad INTEGER DEFAULT 1,
                    FOREIGN KEY (personaje_id) REFERENCES personaje (id),
                    FOREIGN KEY (item_id) REFERENCES tienda_item (id)
                )
            """)
            
            conn.commit()
            print('Tablas de tienda creadas exitosamente.')
        else:
            print('Las tablas de tienda ya existen.')
        
        conn.close()
        print('Migración completada exitosamente.')
        
    except Exception as e:
        print(f'Error durante la migración: {e}')
        if conn:
            conn.close()

if __name__ == '__main__':
    migrar_rastamonios() 