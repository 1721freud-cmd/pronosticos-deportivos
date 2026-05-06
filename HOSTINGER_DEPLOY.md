# 🚀 Guía de Despliegue en Hostinger

## 📋 Requisitos

- Cuenta de hosting en Hostinger (con soporte Python)
- Dominio: ivanchelo.fun
- Acceso a cPanel

---

## 📁 Estructura de Archivos

Sube estos archivos a tu hosting:

```
public_html/
├── app.py
├── passenger_wsgi.py
├── requirements.txt
├── .env
├── .htaccess
├── templates/
│   └── index.html
└── static/
```

---

## 🔧 Pasos de Instalación

### 1. Subir los archivos

1. Entra a cPanel de Hostinger
2. Ve a **Administrador de Archivos**
3. Entra a `public_html`
4. Sube todos los archivos del proyecto

### 2. Configurar el entorno virtual

En cPanel, abre **Terminal** y ejecuta:

```bash
# Crear entorno virtual
python3 -m venv venv

# Activar entorno
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### 3. Configurar la API Key

Crea el archivo `.env` en `public_html`:

```env
ODDS_API_KEY=a6df61fd2d9b2947e816f2a878198103
```

### 4. Configurar Passenger

Crea el archivo `.htaccess` en `public_html`:

```apache
PassengerAppRoot /home/TU_USUARIO/public_html
PassengerPython /home/TU_USUARIO/venv/bin/python3
PassengerAppType wsgi
PassengerStartupFile passenger_wsgi.py
```

**Importante:** Reemplaza `TU_USUARIO` con tu nombre de usuario real de Hostinger.

### 5. Configurar el dominio

1. En cPanel, ve a **Dominios**
2. Asegúrate que `ivanchelo.fun` apunte a `public_html`
3. Si es un subdominio, configúralo en **Subdominios**

### 6. Verificar la instalación

En cPanel → **Seleccionar versión de Python**:
- Selecciona Python 3.11 o superior
- Apunta a `public_html/passenger_wsgi.py`

---

## 🐛 Solución de Problemas

### Error 500 - Internal Server Error

1. Revisa los logs en cPanel → **Errores**
2. Verifica que `.env` exista y tenga la API Key correcta
3. Asegúrate que el entorno virtual esté activado

### La página no carga

1. Verifica que `.htaccess` tenga la ruta correcta
2. Revisa que `passenger_wsgi.py` exista
3. Verifica los permisos de archivos (755 para carpetas, 644 para archivos)

### Error de Python

1. En cPanel → **Setup Python App**
2. Revisa la versión de Python (mínimo 3.8)
3. Verifica que las dependencias estén instaladas

---

## 📊 Optimización de Requests

**Configuración actual:**
- Cache: 2 horas
- Requests: 2 cada 2 horas
- Total: ~24 requests/día = ~720 requests/mes

**Límite The Odds API:** 500 requests/mes

Si excedes el límite, aumenta el cache a 3 horas:
```python
CACHE_DURATION = 10800  # 3 horas
```

---

## 🔒 Seguridad

1. **No subas** `.git` ni archivos de desarrollo
2. **Protege** el archivo `.env` (no debe ser accesible desde web)
3. Usa HTTPS (Hostinger lo incluye gratis con Let's Encrypt)

---

## 📞 Soporte Hostinger

- Panel: cPanel
- Documentación: https://support.hostinger.com/
- Chat 24/7 disponible

---

## ✅ Checklist antes de ir a producción

- [ ] Todos los archivos subidos
- [ ] `.env` configurado con API Key
- [ ] Entorno virtual creado y dependencias instaladas
- [ ] `.htaccess` configurado con rutas correctas
- [ ] Dominio apuntando a `public_html`
- [ ] HTTPS activado
- [ ] Probar la página en ivanchelo.fun
