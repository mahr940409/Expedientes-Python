import sqlite3

DB_PATH = 'instance/expedientes.db'

SQL = """
ALTER TABLE usuario ADD COLUMN slots_comprados INTEGER DEFAULT 0;
"""

def main():
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(usuario)")
        columnas = [row[1] for row in cur.fetchall()]
        if 'slots_comprados' not in columnas:
            cur.execute(SQL)
            conn.commit()
            print('✅ Columna slots_comprados agregada exitosamente')
        else:
            print('ℹ️ La columna slots_comprados ya existe')
        conn.close()
    except Exception as e:
        print(f'❌ Error durante la migración: {e}')

if __name__ == '__main__':
    main() 