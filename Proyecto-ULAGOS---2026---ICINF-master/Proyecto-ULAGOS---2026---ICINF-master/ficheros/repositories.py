"""
PATRÓN DE DISEÑO 1: REPOSITORY
Desacopla el acceso a datos de la lógica de negocio (SOLID: DIP, SRP).
Todas las consultas a la BD pasan por aquí; los controladores nunca tocan .query directamente.
"""
from abc import ABC, abstractmethod
from datetime import datetime, date
from sqlalchemy import func

from .configr import db
from .Modelos import User, Menu, Snack, Pedido


# ─── Interfaz base (SOLID: ISP — interfaces pequeñas y focalizadas) ───────────
class BaseRepository(ABC):
    """Contrato mínimo que todo repositorio debe cumplir."""

    @abstractmethod
    def get_all(self):  pass

    @abstractmethod
    def get_by_id(self, id):  pass

    def save(self, entity):
        db.session.add(entity)
        db.session.commit()
        return entity

    def delete(self, entity):
        db.session.delete(entity)
        db.session.commit()


# ─── UserRepository ───────────────────────────────────────────────────────────
class UserRepository(BaseRepository):
    def get_all(self):             return User.query.all()
    def get_by_id(self, rut):     return User.query.filter_by(rut=rut).first()
    def exists(self, rut):        return self.get_by_id(rut) is not None
    def authenticate(self, rut, pw): return User.get(rut, pw)
    def as_dict(self):
        return {str(u.rut): {'role': 'admin' if u.role else 'user'} for u in self.get_all()}


# ─── MenuRepository ───────────────────────────────────────────────────────────
class MenuRepository(BaseRepository):
    _DAY_NAMES = ['lunes','martes','miercoles','jueves','viernes','sabado','domingo']

    def get_all(self):
        order = {d: i for i, d in enumerate(self._DAY_NAMES)}
        menus = Menu.query.all()
        return sorted(menus, key=lambda m: order.get(m.day, 99))

    def get_by_id(self, id):   return Menu.query.get(id)
    def get_by_day(self, day): return Menu.query.filter_by(day=day).first()

    def get_today(self):
        today_key = self._DAY_NAMES[datetime.now().weekday()]
        return self.get_by_day(today_key)

    def reducir_stock(self, menu_id: int, field: str):
        m = self.get_by_id(menu_id)
        if m:
            attr = f'stock_{field}'
            val  = getattr(m, attr, 0)
            if val > 0:
                setattr(m, attr, val - 1)
                db.session.commit()

    def to_json(self, menu: Menu) -> dict:
        if not menu: return {}
        return {
            'time': menu.time,
            'menu1': menu.menu1,       'precio_menu1': menu.precio_menu1,       'stock_menu1': menu.stock_menu1,
            'menu2': menu.menu2,       'precio_menu2': menu.precio_menu2,       'stock_menu2': menu.stock_menu2,
            'hipocalorico': menu.hipocalorico, 'precio_hipocalorico': menu.precio_hipocalorico, 'stock_hipocalorico': menu.stock_hipocalorico,
            'vegetariano':  menu.vegetariano,  'precio_vegetariano':  menu.precio_vegetariano,  'stock_vegetariano':  menu.stock_vegetariano,
        }


# ─── SnackRepository ──────────────────────────────────────────────────────────
CATEGORIAS = ['cafes','sandwiches','reposteria','snacks','bebidas','jugos']

class SnackRepository(BaseRepository):
    def get_all(self):                  return Snack.query.all()
    def get_by_id(self, id):            return Snack.query.get(id)
    def get_by_cat(self, cat):          return Snack.query.filter_by(categoria=cat).all()

    def get_as_dict(self) -> dict:
        """Devuelve snacks agrupados por categoría para los templates."""
        result = {}
        for cat in CATEGORIAS:
            items = self.get_by_cat(cat)
            result[cat] = [
                {
                    'id': s.id, 'nombre': s.nombre, 'desc': s.descripcion,
                    'img': s.img, 'stock': s.stock, 'precio': s.precio,
                    **(  # cafés tienen precio regular/grande
                        {'precio_regular': s.precio, 'precio_grande': s.precio_grande}
                        if cat == 'cafes' else {}
                    )
                }
                for s in items
            ]
        return result

    def reducir_stock(self, snack_id: int):
        s = self.get_by_id(snack_id)
        if s and s.stock > 0:
            s.stock -= 1
            db.session.commit()


# ─── PedidoRepository ─────────────────────────────────────────────────────────
class PedidoRepository(BaseRepository):
    def get_all(self):            return Pedido.query.order_by(Pedido.fecha.desc()).all()
    def get_by_id(self, id):     return Pedido.query.get(id)

    def get_by_user(self, rut):
        return (Pedido.query
                .filter_by(usuario_rut=rut)
                .filter(Pedido.estado != 'cancelado')
                .order_by(Pedido.fecha.desc()).all())

    def get_recent(self, limit=20):
        return Pedido.query.order_by(Pedido.fecha.desc()).limit(limit).all()

    def get_stats(self) -> dict:
        hoy       = date.today()
        ini_mes   = hoy.replace(day=1)
        _sum      = lambda q: q.scalar() or 0

        ventas_hoy = _sum(db.session.query(func.sum(Pedido.precio)).filter(
            func.date(Pedido.fecha) == hoy, Pedido.estado != 'cancelado'))

        ventas_mes = _sum(db.session.query(func.sum(Pedido.precio)).filter(
            Pedido.fecha >= datetime.combine(ini_mes, datetime.min.time()),
            Pedido.estado != 'cancelado'))

        return {
            'ventas_hoy': ventas_hoy,
            'ventas_mes': ventas_mes,
            'pendientes': Pedido.query.filter_by(estado='pendiente').count(),
            'entregados': Pedido.query.filter_by(estado='entregado').count(),
        }
