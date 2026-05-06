import sys
import os

# Agregar el directorio de la aplicación al path
sys.path.insert(0, os.path.dirname(__file__))

from app import app as application

# Configuración para Passenger
application.debug = False
