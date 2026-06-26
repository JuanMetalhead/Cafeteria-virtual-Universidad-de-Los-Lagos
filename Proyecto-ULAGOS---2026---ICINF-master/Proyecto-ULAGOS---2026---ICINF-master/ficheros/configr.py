import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Configuración de la app
app = Flask(__name__, template_folder='templates')

# SECRET KEY — necesaria para usar session y flash
app.secret_key = 'ulagos_cafeteria_2026_clave_secreta'


# =============================================================================
# CONFIGURACIÓN DE LA BASE DE DATOS:
# Se define la ruta exacta donde se guardará el archivo 'database.db' (SQLite)
# y se conecta la herramienta SQLAlchemy a nuestra aplicación.
# =============================================================================
dbdir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(dbdir, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
