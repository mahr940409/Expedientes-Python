# Sistema de Gestión de Expedientes Digitales

Una aplicación web completa para gestionar expedientes digitales de personajes, armas, invocaciones, planetas y elementos, desarrollada con Flask y SQLAlchemy.

## 🚀 Características Principales

### 👥 Gestión de Usuarios
- **Sistema de registro y login** con autenticación segura
- **Roles de usuario**: Usuarios normales y Administradores
- **Límite de personajes**: Usuarios normales pueden crear hasta 3 personajes
- **Permisos granulares**: Solo el creador del personaje o el administrador pueden editarlo

### 🎭 Gestión de Personajes
- **Crear, editar, eliminar** personajes con fotografía obligatoria
- **Atributos completos**: Nombre, dimensión, planeta, edad, descripción, nivel, rango
- **Asignación de elementos** con interfaz dinámica
- **Validación de datos** y manejo de errores

### ⚔️ Gestión de Armas e Invocaciones
- **Agregar armas** a personajes con imagen, descripción, rango y nivel
- **Agregar invocaciones** con imagen, descripción, rango y elementos
- **Eliminar** armas e invocaciones individualmente
- **Visualización** en tarjetas con imágenes

### 🌍 Gestión de Planetas
- **Crear, editar, eliminar** planetas por dimensión
- **Asignación automática** a personajes del universo
- **Validación** para evitar planetas duplicados
- **Solo administradores** pueden gestionar planetas

### 🔥 Gestión de Elementos
- **Crear, editar, eliminar** elementos
- **Asignación múltiple** a personajes e invocaciones
- **Interfaz visual** con badges de colores
- **Solo administradores** pueden gestionar elementos

## 🛠️ Tecnologías Utilizadas

- **Backend**: Flask, SQLAlchemy, SQLite
- **Frontend**: HTML5, CSS3, Bootstrap 5, JavaScript
- **Autenticación**: Session-based con Flask
- **Base de Datos**: SQLite con migraciones automáticas
- **Subida de archivos**: Manejo seguro de imágenes

## 📁 Estructura del Proyecto

```
Expedientes/
├── app.py                 # Aplicación principal Flask
├── models.py              # Modelos de base de datos
├── requirements.txt       # Dependencias Python
├── README.md             # Documentación
├── .gitignore            # Archivos ignorados por Git
├── templates/            # Plantillas HTML
│   ├── base.html         # Plantilla base
│   ├── index.html        # Página principal
│   ├── login.html        # Página de login
│   ├── register.html     # Página de registro
│   ├── ver_personaje.html # Vista detallada de personaje
│   ├── nuevo_personaje.html # Crear personaje
│   ├── editar_personaje.html # Editar personaje
│   ├── planetas.html     # Lista de planetas
│   ├── nuevo_planeta.html # Crear planeta
│   ├── editar_planeta.html # Editar planeta
│   ├── elementos.html    # Lista de elementos
│   └── nuevo_elemento.html # Crear elemento
├── static/               # Archivos estáticos
│   ├── uploads/          # Imágenes subidas
│   └── css/              # Estilos CSS
└── instance/             # Base de datos SQLite
```

## 🚀 Instalación y Configuración

### Prerrequisitos
- Python 3.7 o superior
- pip (gestor de paquetes de Python)

### Pasos de Instalación

1. **Clonar o descargar el proyecto**
   ```bash
   git clone <url-del-repositorio>
   cd Expedientes
   ```

2. **Instalar dependencias**
   ```bash
   pip install -r requirements.txt
   ```

3. **Ejecutar la aplicación**
   ```bash
   py app.py
   ```

4. **Acceder a la aplicación**
   - Abrir navegador en: `http://localhost:5000`
   - O en red local: `http://192.168.1.10:5000`

## 👤 Usuarios por Defecto

### Administrador
- **Usuario**: Burs
- **Contraseña**: admin123
- **Permisos**: Completos (editar cualquier personaje, gestionar planetas y elementos)

### Usuario Normal
- **Usuario**: Manuel Hernandez
- **Contraseña**: (configurada durante el registro)
- **Permisos**: Solo puede editar sus propios personajes (máximo 3)

## 🔐 Sistema de Seguridad

### Autenticación
- **Sesiones seguras** con Flask
- **Contraseñas hasheadas** con bcrypt
- **Protección CSRF** implícita

### Autorización
- **Decoradores personalizados** para proteger rutas
- **Verificación de permisos** en cada operación
- **Redirección automática** a login si no autorizado

### Validación de Datos
- **Validación de formularios** en frontend y backend
- **Sanitización de archivos** subidos
- **Verificación de tipos** de archivo permitidos

## 🎨 Características de la Interfaz

### Diseño Responsivo
- **Bootstrap 5** para diseño moderno y responsive
- **Iconos FontAwesome** para mejor UX
- **Colores temáticos** para diferentes elementos

### Experiencia de Usuario
- **Navegación intuitiva** con breadcrumbs
- **Mensajes flash** para feedback al usuario
- **Confirmaciones** para acciones destructivas
- **Carga dinámica** de elementos con AJAX

## 📊 Funcionalidades Avanzadas

### Gestión de Imágenes
- **Subida automática** de imágenes con nombres únicos
- **Validación de formatos** (PNG, JPG, JPEG, GIF, WEBP)
- **Almacenamiento organizado** en carpeta uploads

### Relaciones de Datos
- **Relaciones ORM** entre todas las entidades
- **Integridad referencial** en la base de datos
- **Cascada de eliminación** cuando es apropiado

### API Interna
- **Endpoints AJAX** para carga dinámica de datos
- **JSON responses** para elementos y planetas
- **Filtros de plantilla** personalizados

## 🔧 Mantenimiento

### Base de Datos
- **SQLite** para desarrollo y uso local
- **Migraciones automáticas** al iniciar la aplicación
- **Backup automático** de datos importantes

### Logs y Debugging
- **Modo debug** habilitado para desarrollo
- **Mensajes de error** descriptivos
- **Validación de datos** en tiempo real

## 🚀 Despliegue

### Desarrollo Local
```bash
py app.py
```

### Producción
- Usar WSGI server (Gunicorn, uWSGI)
- Configurar variables de entorno
- Usar base de datos PostgreSQL/MySQL
- Configurar proxy reverso (Nginx)

## 📝 Notas de Desarrollo

- **Código limpio** y bien documentado
- **Separación de responsabilidades** (MVC)
- **Manejo de errores** robusto
- **Escalabilidad** para futuras funcionalidades

## 🤝 Contribución

1. Fork el proyecto
2. Crear rama para nueva funcionalidad
3. Commit los cambios
4. Push a la rama
5. Abrir Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo LICENSE para más detalles.

---

**Desarrollado con ❤️ para la gestión eficiente de expedientes digitales** 