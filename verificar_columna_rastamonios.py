import sqlite3

DB_PATH = 'instance/app.db'

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

c.execute("PRAGMA table_info(personaje);")
columnas = [col[1] for col in c.fetchall()]

if 'rastamonios' in columnas:
    print('✅ La columna rastamonios SÍ existe en la tabla personaje.')
else:
    print('❌ La columna rastamonios NO existe en la tabla personaje.')

conn.close() 