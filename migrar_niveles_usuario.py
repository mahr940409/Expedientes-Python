import sqlite3

DB_PATH = 'instance/expedientes.db'  # Usar la base de datos real

SQL = """
ALTER TABLE usuario ADD COLUMN nivel_usuario VARCHAR(20) DEFAULT 'normal';
"""

def main():
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(usuario)")
        columnas = [row[1] for row in cur.fetchall()]
        if 'nivel_usuario' not in columnas:
            cur.execute(SQL)
            conn.commit()
            print('✅ Columna nivel_usuario agregada exitosamente')
        else:
            print('ℹ️ La columna nivel_usuario ya existe')
        conn.close()
    except Exception as e:
        print(f'❌ Error durante la migración: {e}')

if __name__ == '__main__':
    main() 