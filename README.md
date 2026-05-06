# 🎯 Pronósticos Deportivos - Fútbol & NBA

Aplicación web que analiza partidos de fútbol y NBA usando cuotas reales de casas de apuestas para generar pronósticos inteligentes.

## 🚀 Características

- **Análisis en tiempo real** de partidos de fútbol (Premier League) y NBA
- **Detección de favoritos claros** (equipos con ≥60% de probabilidad de victoria)
- **La Combinada del Día** - Top 3 pronósticos más seguros
- **Interfaz moderna** con Dark Mode
- **Niveles de confianza** basados en cuotas de casas de apuestas

## 📋 Requisitos Previos

- Python 3.8 o superior
- Una API Key gratuita de [The Odds API](https://the-odds-api.com/)

## 🔧 Instalación Paso a Paso

### 1. Obtener tu API Key

1. Ve a [https://the-odds-api.com/](https://the-odds-api.com/)
2. Regístrate gratuitamente (es gratis para uso personal)
3. Copia tu API Key desde el dashboard

### 2. Configurar el proyecto

Abre una terminal en la carpeta `pronosticos-deportivos` y ejecuta:

```bash
# Crear un entorno virtual (recomendado)
python -m venv venv

# Activar el entorno virtual
# En Windows:
venv\Scripts\activate
# En Mac/Linux:
source venv/bin/activate

# Instalar las dependencias
pip install -r requirements.txt
```

### 3. Configurar tu API Key

Crea un archivo llamado `.env` en la carpeta del proyecto y añade:

```env
ODDS_API_KEY=tu_api_key_aqui
```

**Ejemplo:**
```env
ODDS_API_KEY=abc123def456ghi789
```

### 4. Ejecutar la aplicación

```bash
python app.py
```

Verás este mensaje:
```
🚀 Iniciando servidor de pronósticos deportivos...
📊 Abre http://localhost:5000 en tu navegador
```

### 5. Ver la web

Abre tu navegador y ve a: **http://localhost:5000**

## 📊 Cómo Funciona el Sistema de Pronósticos

### Cálculo de Confianza

El sistema analiza las cuotas de las casas de apuestas:

1. **Convierte cuotas a probabilidades**: `Probabilidad = 1 / Cuota`
2. **Identifica el resultado más probable**
3. **Calcula el nivel de confianza** como porcentaje

### Clasificación de Pronósticos

| Nivel de Confianza | Color | Significado |
|-------------------|-------|-------------|
| ≥ 60% | 🟢 Verde | **Favorito Claro** - Alta probabilidad |
| 50-59% | 🟡 Amarillo | Moderado - Probabilidad media |
| < 50% | 🔴 Rojo | Baja - Partido muy equilibrado |

### La Combinada del Día

El sistema selecciona automáticamente los **3 partidos con mayor confianza** (solo aquellos ≥60%) para crear una combinada segura.

## 🎨 Características de la Interfaz

- **Tarjetas de partidos** con información completa
- **Barra de confianza** visual para cada partido
- **Filtros** por deporte (Fútbol/NBA) y favoritos
- **Actualización automática** cada 5 minutos
- **Botón de actualización manual**

## 📁 Estructura del Proyecto

```
pronosticos-deportivos/
├── app.py              # Backend Flask
├── requirements.txt    # Dependencias
├── .env                # Tu API Key (crear este archivo)
├── .env.example       # Ejemplo de configuración
├── templates/
│   └── index.html     # Frontend
└── static/            # Archivos estáticos (vacío por ahora)
```

## 🔍 Solución de Problemas

### Error: "Error al cargar los datos"

- Verifica que tu API Key sea correcta en el archivo `.env`
- Asegúrate de tener conexión a internet
- The Odds API tiene límites de solicitudes gratuitas (500/mes)

### No aparecen partidos

- Puede que no haya partidos programados hoy
- La API solo muestra partidos próximos (no pasados)
- Intenta actualizar manualmente con el botón "Actualizar"

### Error de puerto 5000 en uso

Cambia el puerto en `app.py` (línea final):
```python
app.run(debug=True, host='0.0.0.0', port=5001)  # Cambia 5000 por otro puerto
```

## ⚠️ Aviso Legal

Los pronósticos se basan únicamente en cuotas de casas de apuestas y no garantizan resultados. Apuesta de forma responsable.

## 📞 Soporte

Si tienes problemas, verifica:
1. Python versión 3.8+
2. API Key correcta en `.env`
3. Dependencias instaladas correctamente
