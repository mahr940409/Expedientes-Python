#!/usr/bin/env python3
"""
Script de prueba para verificar el sistema de elementos desbloqueables
"""

import requests
import json

BASE_URL = "http://localhost:5000"

def test_login(username, password):
    """Probar login y obtener sesión"""
    session = requests.Session()
    
    # Obtener página de login
    response = session.get(f"{BASE_URL}/login")
    if response.status_code != 200:
        print(f"❌ Error accediendo al login: {response.status_code}")
        return None
    
    # Hacer login
    login_data = {
        'username': username,
        'password': password
    }
    
    response = session.post(f"{BASE_URL}/login", data=login_data, allow_redirects=False)
    if response.status_code == 302:  # Redirect después del login exitoso
        print(f"✅ Login exitoso para {username}")
        return session
    else:
        print(f"❌ Error en login para {username}: {response.status_code}")
        return None

def test_elementos_disponibles(session, personaje_id):
    """Probar API de elementos disponibles"""
    response = session.get(f"{BASE_URL}/api/elementos-disponibles/{personaje_id}")
    
    if response.status_code == 200:
        elementos = response.json()
        print(f"✅ Elementos disponibles para personaje {personaje_id}:")
        for elem in elementos:
            tipo = "Básico" if elem['es_basico'] else "Avanzado"
            print(f"  - {elem['nombre']} ({tipo})")
        return elementos
    else:
        print(f"❌ Error obteniendo elementos: {response.status_code}")
        return None

def test_crear_solicitud(session, elemento_id, personaje_id, motivo):
    """Probar creación de solicitud"""
    solicitud_data = {
        'elemento_id': elemento_id,
        'personaje_id': personaje_id,
        'motivo': motivo
    }
    
    response = session.post(f"{BASE_URL}/solicitud/nueva", data=solicitud_data, allow_redirects=False)
    
    if response.status_code == 302:  # Redirect después de crear solicitud
        print(f"✅ Solicitud creada exitosamente")
        return True
    else:
        print(f"❌ Error creando solicitud: {response.status_code}")
        return False

def main():
    print("🧪 Probando sistema de elementos desbloqueables...")
    print("=" * 50)
    
    # Probar login de usuario normal
    print("\n1. Probando login de usuario normal...")
    session_normal = test_login("usuario_normal", "Hinata9404")
    
    if not session_normal:
        print("❌ No se pudo hacer login con usuario normal")
        return
    
    # Probar elementos disponibles (debería mostrar solo básicos)
    print("\n2. Probando elementos disponibles para usuario normal...")
    elementos = test_elementos_disponibles(session_normal, 1)
    
    if elementos:
        elementos_basicos = [e for e in elementos if e['es_basico']]
        elementos_avanzados = [e for e in elementos if not e['es_basico']]
        
        print(f"\n📊 Resumen:")
        print(f"  - Elementos básicos disponibles: {len(elementos_basicos)}")
        print(f"  - Elementos avanzados disponibles: {len(elementos_avanzados)}")
        
        if len(elementos_avanzados) > 0:
            print("⚠️  ADVERTENCIA: Usuario normal tiene acceso a elementos avanzados!")
        else:
            print("✅ CORRECTO: Usuario normal solo tiene acceso a elementos básicos")
    
    # Probar login de administrador
    print("\n3. Probando login de administrador...")
    session_admin = test_login("Burs", "Hinata9404")
    
    if not session_admin:
        print("❌ No se pudo hacer login con administrador")
        return
    
    # Probar elementos disponibles para admin (debería mostrar todos)
    print("\n4. Probando elementos disponibles para administrador...")
    elementos_admin = test_elementos_disponibles(session_admin, 1)
    
    if elementos_admin:
        elementos_basicos_admin = [e for e in elementos_admin if e['es_basico']]
        elementos_avanzados_admin = [e for e in elementos_admin if not e['es_basico']]
        
        print(f"\n📊 Resumen para administrador:")
        print(f"  - Elementos básicos disponibles: {len(elementos_basicos_admin)}")
        print(f"  - Elementos avanzados disponibles: {len(elementos_avanzados_admin)}")
        
        if len(elementos_avanzados_admin) > 0:
            print("✅ CORRECTO: Administrador tiene acceso a elementos avanzados")
        else:
            print("⚠️  ADVERTENCIA: Administrador no tiene acceso a elementos avanzados")
    
    print("\n" + "=" * 50)
    print("🎯 Pruebas completadas!")
    
    if session_normal:
        session_normal.close()
    if session_admin:
        session_admin.close()

if __name__ == '__main__':
    main() 