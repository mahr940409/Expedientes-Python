#!/usr/bin/env python3
"""
Script para migrar la base de datos y agregar la tabla de mensajes.
"""

import sqlite3
import os

def migrar_mensajeria():
    """Migra la base de datos para agregar la tabla mensaje"""
    
    db_path = 'instance/expedientes.db'
    
    if not os.path.exists(db_path):
        print("❌ No se encontró la base de datos. Asegúrate de que la aplicación se haya ejecutado al menos una vez.")
        return False
    
    try:
        # Conectar a la base de datos
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar si la tabla mensaje ya existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='mensaje'")
        if cursor.fetchone():
            print("✅ La tabla 'mensaje' ya existe")
            return True
        
        print("🔄 Creando tabla 'mensaje'...")
        
        # Crear la tabla mensaje
        cursor.execute("""
            CREATE TABLE mensaje (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                remitente_id INTEGER NOT NULL,
                destinatario_id INTEGER NOT NULL,
                asunto VARCHAR(200) NOT NULL,
                contenido TEXT NOT NULL,
                fecha_envio DATETIME DEFAULT CURRENT_TIMESTAMP,
                leido BOOLEAN DEFAULT 0,
                FOREIGN KEY (remitente_id) REFERENCES personaje (id),
                FOREIGN KEY (destinatario_id) REFERENCES personaje (id)
            )
        """)
        
        # Crear índices para mejorar el rendimiento
        cursor.execute("CREATE INDEX idx_mensaje_remitente ON mensaje(remitente_id)")
        cursor.execute("CREATE INDEX idx_mensaje_destinatario ON mensaje(destinatario_id)")
        cursor.execute("CREATE INDEX idx_mensaje_fecha ON mensaje(fecha_envio)")
        cursor.execute("CREATE INDEX idx_mensaje_leido ON mensaje(leido)")
        
        # Confirmar cambios
        conn.commit()
        
        # Verificar que se creó correctamente
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='mensaje'")
        if cursor.fetchone():
            print("✅ Migración completada exitosamente")
            print("📊 Tabla 'mensaje' creada con:")
            print("   - Campo id (PRIMARY KEY)")
            print("   - Campo remitente_id (FOREIGN KEY)")
            print("   - Campo destinatario_id (FOREIGN KEY)")
            print("   - Campo asunto (VARCHAR)")
            print("   - Campo contenido (TEXT)")
            print("   - Campo fecha_envio (DATETIME)")
            print("   - Campo leido (BOOLEAN)")
            print("   - Índices para optimizar consultas")
            
            return True
        else:
            print("❌ Error: No se pudo crear la tabla mensaje")
            return False
            
    except sqlite3.Error as e:
        print(f"❌ Error de SQLite: {e}")
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("🚀 Iniciando migración de mensajería...")
    print("=" * 50)
    
    if migrar_mensajeria():
        print("=" * 50)
        print("🎉 Migración completada. El sistema de mensajería está listo para usar.")
        print("\n📝 Funcionalidades disponibles:")
        print("   - Enviar mensajes entre personajes")
        print("   - Ver mensajes recibidos y enviados")
        print("   - Marcar mensajes como leídos")
        print("   - Eliminar mensajes")
        print("   - Contador de mensajes no leídos")
    else:
        print("=" * 50)
        print("💥 La migración falló. Revisa los errores anteriores.") 