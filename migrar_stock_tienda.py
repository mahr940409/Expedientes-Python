#!/usr/bin/env python3
"""
Script para migrar la base de datos y agregar el campo stock a los items de la tienda.
Los items únicos mantienen stock = -1 (ilimitado), los normales se establecen en stock = -1 (ilimitado) por defecto.
"""

import sqlite3
import os

def migrar_stock_tienda():
    """Migra la base de datos para agregar el campo stock a la tabla tienda_item"""
    
    db_path = 'instance/expedientes.db'
    
    if not os.path.exists(db_path):
        print("❌ No se encontró la base de datos. Asegúrate de que la aplicación se haya ejecutado al menos una vez.")
        return False
    
    try:
        # Conectar a la base de datos
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar si la columna stock ya existe
        cursor.execute("PRAGMA table_info(tienda_item)")
        columnas = [col[1] for col in cursor.fetchall()]
        
        if 'stock' in columnas:
            print("✅ La columna 'stock' ya existe en la tabla tienda_item")
            return True
        
        print("🔄 Agregando columna 'stock' a la tabla tienda_item...")
        
        # Agregar la columna stock
        cursor.execute("ALTER TABLE tienda_item ADD COLUMN stock INTEGER DEFAULT -1")
        
        # Actualizar items existentes
        # Items únicos: stock = -1 (ilimitado, ya que solo puede haber uno)
        # Items normales: stock = -1 (ilimitado por defecto, se puede cambiar manualmente)
        cursor.execute("""
            UPDATE tienda_item 
            SET stock = -1 
            WHERE stock IS NULL
        """)
        
        # Confirmar cambios
        conn.commit()
        
        # Verificar que se agregó correctamente
        cursor.execute("PRAGMA table_info(tienda_item)")
        columnas_actualizadas = [col[1] for col in cursor.fetchall()]
        
        if 'stock' in columnas_actualizadas:
            print("✅ Migración completada exitosamente")
            print("📊 Items actualizados:")
            
            # Mostrar estadísticas
            cursor.execute("SELECT COUNT(*) FROM tienda_item")
            total_items = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM tienda_item WHERE es_unico = 1")
            items_unicos = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM tienda_item WHERE es_unico = 0")
            items_normales = cursor.fetchone()[0]
            
            print(f"   - Total de items: {total_items}")
            print(f"   - Items únicos: {items_unicos}")
            print(f"   - Items normales: {items_normales}")
            print(f"   - Todos configurados con stock ilimitado (-1) por defecto")
            
            return True
        else:
            print("❌ Error: No se pudo agregar la columna stock")
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
    print("🚀 Iniciando migración de stock para la tienda...")
    print("=" * 50)
    
    if migrar_stock_tienda():
        print("=" * 50)
        print("🎉 Migración completada. La aplicación está lista para usar el sistema de stock.")
        print("\n📝 Notas:")
        print("   - Los items únicos mantienen stock ilimitado")
        print("   - Los items normales tienen stock ilimitado por defecto")
        print("   - Puedes editar el stock de cada item desde el panel de administración")
    else:
        print("=" * 50)
        print("💥 La migración falló. Revisa los errores anteriores.") 