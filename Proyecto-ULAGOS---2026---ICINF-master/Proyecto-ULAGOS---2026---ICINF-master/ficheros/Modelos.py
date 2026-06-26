"""
Modelos de base de datos — Principio SRP (SOLID):
Cada clase tiene una sola responsabilidad (representar una tabla).
"""
from .configr import db
from datetime import datetime
import random, string

try:
    from zoneinfo import ZoneInfo
    _TZ_CHILE = ZoneInfo('America/Santiago')
except Exception:
    _TZ_CHILE = None

# ─── Utilidad ─────────────────────────────────────────────────────────────────
def generar_codigo() -> str:
    sufijo = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f'ULG-{sufijo}'

def ahora_chile() -> datetime:
    """
    Hora actual en la zona horaria de Chile (America/Santiago).
    Se usa en vez de datetime.utcnow()/datetime.now() para que la hora
    guardada en la BD sea siempre la hora real de la compra, sin importar
    en qué zona horaria esté configurado el servidor donde corra la app.
    """
    if _TZ_CHILE is not None:
        return datetime.now(_TZ_CHILE).replace(tzinfo=None)
    return datetime.now()

# Imágenes de respaldo para almuerzos
IMG_PLATOS = {
    'menu1':        'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?q=80&w=800&auto=format&fit=crop',
    'menu2':        'https://images.unsplash.com/photo-1512621776951-a57141f2eefd?q=80&w=800&auto=format&fit=crop',
    'hipocalorico': 'https://images.unsplash.com/photo-1490645935967-10de6ba17061?q=80&w=800&auto=format&fit=crop',
    'vegetariano':  'https://images.unsplash.com/photo-1473093295043-cdd812d0e601?q=80&w=800&auto=format&fit=crop',
}

# ─── Usuario ──────────────────────────────────────────────────────────────────
class User(db.Model):
    __tablename__ = 'user'
    rut      = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(70),  nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role     = db.Column(db.Boolean, default=False)   # True = admin

    @classmethod
    def get(cls, rut, password):
        try:
            u = cls.query.filter_by(rut=int(rut)).first()
            if u and u.password == password:
                return u
        except (ValueError, TypeError):
            pass
        return None

# ─── Menú de Almuerzo ─────────────────────────────────────────────────────────
class Menu(db.Model):
    __tablename__ = 'menu'
    id   = db.Column(db.Integer, primary_key=True)
    day  = db.Column(db.String(15), nullable=False, unique=True)
    time = db.Column(db.String(5),  default='12:00')

    menu1        = db.Column(db.String(200), nullable=False)
    menu2        = db.Column(db.String(200), nullable=False)
    hipocalorico = db.Column(db.String(200), nullable=False)
    vegetariano  = db.Column(db.String(200), nullable=False)

    precio_menu1        = db.Column(db.Integer, default=4500)
    precio_menu2        = db.Column(db.Integer, default=5200)
    precio_hipocalorico = db.Column(db.Integer, default=4200)
    precio_vegetariano  = db.Column(db.Integer, default=4800)

    stock_menu1        = db.Column(db.Integer, default=20)
    stock_menu2        = db.Column(db.Integer, default=20)
    stock_hipocalorico = db.Column(db.Integer, default=20)
    stock_vegetariano  = db.Column(db.Integer, default=20)

    def to_platos(self) -> list:
        """Devuelve los 4 platos del menú como lista de dicts para los templates."""
        return [
            {'label': 'Almuerzo 1',  'field': 'menu1',        'nombre': self.menu1,
             'precio': self.precio_menu1,        'stock': self.stock_menu1,        'img': IMG_PLATOS['menu1']},
            {'label': 'Almuerzo 2',  'field': 'menu2',        'nombre': self.menu2,
             'precio': self.precio_menu2,        'stock': self.stock_menu2,        'img': IMG_PLATOS['menu2']},
            {'label': 'Hipocalórico','field': 'hipocalorico', 'nombre': self.hipocalorico,
             'precio': self.precio_hipocalorico, 'stock': self.stock_hipocalorico, 'img': IMG_PLATOS['hipocalorico']},
            {'label': 'Vegetariano', 'field': 'vegetariano',  'nombre': self.vegetariano,
             'precio': self.precio_vegetariano,  'stock': self.stock_vegetariano,  'img': IMG_PLATOS['vegetariano']},
        ]

# ─── Snack / Producto ─────────────────────────────────────────────────────────
class Snack(db.Model):
    __tablename__ = 'snack'
    id            = db.Column(db.Integer, primary_key=True)
    nombre        = db.Column(db.String(100), nullable=False)
    categoria     = db.Column(db.String(30),  nullable=False)
    descripcion   = db.Column(db.String(300), default='')
    precio        = db.Column(db.Integer, nullable=False)
    precio_grande = db.Column(db.Integer, nullable=True)   # solo cafés
    stock         = db.Column(db.Integer, default=20)
    img           = db.Column(db.String(500), default='')

# ─── Pedido ───────────────────────────────────────────────────────────────────
class Pedido(db.Model):
    __tablename__ = 'pedido'
    id          = db.Column(db.Integer, primary_key=True)
    usuario_rut = db.Column(db.Integer, db.ForeignKey('user.rut'), nullable=False)
    item_nombre = db.Column(db.String(200), nullable=False)
    item_tipo   = db.Column(db.String(20),  nullable=False)   # almuerzo|snack
    precio      = db.Column(db.Integer, nullable=False, default=0)
    estado      = db.Column(db.String(20), default='pendiente')  # pendiente|entregado|cancelado
    # Se usa ahora_chile() (hora real de Chile, America/Santiago) y no datetime.utcnow(),
    # para que la hora guardada coincida siempre con la hora real de compra, sin
    # depender de la zona horaria configurada en el servidor donde corra la app.
    fecha       = db.Column(db.DateTime, default=ahora_chile)
    codigo      = db.Column(db.String(15), nullable=False)
    # Método de pago utilizado: ej. "Webpay - Débito", "Webpay - Crédito", "JUNAEB Edenred"
    metodo_pago = db.Column(db.String(40), default='No especificado')
    usuario     = db.relationship('User', backref='pedidos')
