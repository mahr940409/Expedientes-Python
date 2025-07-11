import sqlite3
import os

def migrar_tienda_avanzada():
    """Migrar la base de datos para agregar los nuevos campos de la tienda"""
    
    # Ruta de la base de datos
    db_path = 'instance/expedientes.db'
    
    if not os.path.exists(db_path):
        print('Base de datos no encontrada.')
        return
    
    try:
        # Conectar a la base de datos
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
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
                    disponible BOOLEAN DEFAULT 1,
                    es_unico BOOLEAN DEFAULT 0,
                    poder_adicional INTEGER DEFAULT 0,
                    fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP
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
            
            # Verificar si los nuevos campos existen en tienda_item
            cursor.execute("PRAGMA table_info(tienda_item)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'es_unico' not in columns:
                print('Agregando columna es_unico a tienda_item...')
                cursor.execute("ALTER TABLE tienda_item ADD COLUMN es_unico BOOLEAN DEFAULT 0")
            
            if 'poder_adicional' not in columns:
                print('Agregando columna poder_adicional a tienda_item...')
                cursor.execute("ALTER TABLE tienda_item ADD COLUMN poder_adicional INTEGER DEFAULT 0")
            
            if 'fecha_creacion' not in columns:
                print('Agregando columna fecha_creacion a tienda_item...')
                cursor.execute("ALTER TABLE tienda_item ADD COLUMN fecha_creacion DATETIME")
                # Actualizar registros existentes con fecha actual
                cursor.execute("UPDATE tienda_item SET fecha_creacion = datetime('now') WHERE fecha_creacion IS NULL")
            
            conn.commit()
            print('Campos adicionales agregados exitosamente.')
        
        # Verificar si la columna rastamonios existe en personaje
        cursor.execute("PRAGMA table_info(personaje)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'rastamonios' not in columns:
            print('Agregando columna rastamonios a personaje...')
            cursor.execute("ALTER TABLE personaje ADD COLUMN rastamonios INTEGER DEFAULT 10000")
            cursor.execute("UPDATE personaje SET rastamonios = 10000 WHERE rastamonios IS NULL")
            conn.commit()
            print('Columna rastamonios agregada exitosamente.')
        
        conn.close()
        print('Migración de tienda avanzada completada exitosamente.')
        
    except Exception as e:
        print(f'Error durante la migración: {e}')
        if conn:
            conn.close()

if __name__ == '__main__':
    migrar_tienda_avanzada() 