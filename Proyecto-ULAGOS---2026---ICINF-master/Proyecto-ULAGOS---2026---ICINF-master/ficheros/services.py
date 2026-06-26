"""
PATRÓN DE DISEÑO 2: OBSERVER   — EventManager notifica observers ante eventos de negocio.
PATRÓN DE DISEÑO 3: FACTORY    — PedidoFactory encapsula la creación de pedidos.

Principio OCP (SOLID): nuevos tipos de pedido o nuevos observers se agregan
sin modificar las clases existentes.
"""
from .Modelos import Pedido, generar_codigo
from .configr import db


# ══════════════════════════════════════════════════════════════════════════════
#  PATRÓN OBSERVER
# ══════════════════════════════════════════════════════════════════════════════
class EventManager:
    """Gestor de eventos: registra oyentes y los notifica al ocurrir un evento."""

    def __init__(self):
        self._listeners: dict = {}

    def subscribe(self, event: str, listener):
        self._listeners.setdefault(event, []).append(listener)

    def notify(self, event: str, data: dict):
        for listener in self._listeners.get(event, []):
            listener.update(data)


class StockObserver:
    """
    Observer que reduce el stock en BD cada vez que se registra un pedido.
    Depende de las abstracciones MenuRepository y SnackRepository (SOLID: DIP).
    """

    def __init__(self, menu_repo, snack_repo):
        self._menu_repo  = menu_repo
        self._snack_repo = snack_repo

    def update(self, data: dict):
        tipo = data.get('tipo')
        if tipo == 'almuerzo':
            if data.get('menu_id') and data.get('field'):
                self._menu_repo.reducir_stock(data['menu_id'], data['field'])
        elif tipo == 'snack':
            if data.get('snack_id'):
                self._snack_repo.reducir_stock(data['snack_id'])


# ══════════════════════════════════════════════════════════════════════════════
#  PATRÓN FACTORY
# ══════════════════════════════════════════════════════════════════════════════
class PedidoFactory:
    """
    Fábrica de pedidos: oculta la lógica de construcción de distintos tipos.
    Añadir un nuevo tipo (ej. 'combo') no requiere cambiar el servicio ni
    los controladores — solo agregar un método aquí (SOLID: OCP).
    """

    @staticmethod
    def crear_almuerzo(usuario_rut: int, nombre: str, precio: int,
                       metodo_pago: str = 'webpay_debito') -> Pedido:
        return Pedido(
            usuario_rut=usuario_rut,
            item_nombre=nombre,
            item_tipo='almuerzo',
            precio=precio,
            estado='pendiente',
            codigo=generar_codigo(),
            metodo_pago=metodo_pago,
        )

    @staticmethod
    def crear_snack(usuario_rut: int, nombre: str, precio: int, size: str = None,
                    metodo_pago: str = 'webpay_debito') -> Pedido:
        nombre_completo = f"{nombre}{' - ' + size if size else ''}"
        return Pedido(
            usuario_rut=usuario_rut,
            item_nombre=nombre_completo,
            item_tipo='snack',
            precio=precio,
            estado='pendiente',
            codigo=generar_codigo(),
            metodo_pago=metodo_pago,
        )


# ══════════════════════════════════════════════════════════════════════════════
#  SERVICIO DE PEDIDOS  (orquesta Factory + Repository + Observer)
# ══════════════════════════════════════════════════════════════════════════════
class PedidoService:
    """
    Lógica de negocio de pedidos.
    Depende de abstracciones (repos + event_manager), no de implementaciones (SOLID: DIP).
    """

    def __init__(self, pedido_repo, event_manager: EventManager):
        self._repo   = pedido_repo
        self._events = event_manager

    # ── Registrar un almuerzo ─────────────────────────────────────────────────
    def registrar_almuerzo(self, usuario_rut: int, nombre: str, precio: int,
                           menu_id: int = None, field: str = None,
                           metodo_pago: str = 'webpay_debito') -> Pedido:
        pedido = PedidoFactory.crear_almuerzo(usuario_rut, nombre, precio, metodo_pago)
        db.session.add(pedido)
        db.session.commit()
        self._events.notify('pedido_creado', {'tipo': 'almuerzo', 'menu_id': menu_id, 'field': field})
        return pedido

    # ── Registrar múltiples snacks (carrito) ──────────────────────────────────
    def registrar_multiples_snacks(self, usuario_rut: int, items: list,
                                   metodo_pago: str = 'webpay_debito') -> list:
        codigos = []
        for it in items:
            pedido = PedidoFactory.crear_snack(
                usuario_rut,
                it.get('name', 'Snack'),
                int(it.get('price', 0)),
                it.get('size'),
                metodo_pago,
            )
            db.session.add(pedido)
            codigos.append(pedido.codigo)
            self._events.notify('pedido_creado', {'tipo': 'snack', 'snack_id': it.get('snack_id')})
        db.session.commit()
        return codigos

    # ── Cancelar ──────────────────────────────────────────────────────────────
    def cancelar(self, pedido_id: int, usuario_rut: int) -> bool:
        pedido = self._repo.get_by_id(pedido_id)
        if pedido and pedido.usuario_rut == usuario_rut:
            pedido.estado = 'cancelado'
            db.session.commit()
            return True
        return False

    # ── Marcar entregado ──────────────────────────────────────────────────────
    def marcar_entregado(self, pedido_id: int) -> Pedido:
        pedido = self._repo.get_by_id(pedido_id)
        if pedido:
            pedido.estado = 'entregado'
            db.session.commit()
        return pedido


# ════════════════════════════════════════════
#  UTILIDAD: ESTADO DE INVENTARIO EN PALABRAS 
# ════════════════════════════════════════════
def estado_inventario(stock: int) -> tuple[str, str]:
    """
    Devuelve (etiqueta_profesional, clase_bootstrap) según nivel de stock.
      ≤ 10  → Escasez Crítica        (danger)
      11-19 → Disponibilidad Reducida (warning)
      20-24 → Abastecimiento Regular  (info)
      ≥ 25  → Disponibilidad Óptima   (success)
    """
    if stock <= 10:
        return 'Escasez Crítica',         'danger'
    elif stock <= 19:
        return 'Disponibilidad Reducida', 'warning'
    elif stock <= 24:
        return 'Abastecimiento Regular',  'info'
    else:
        return 'Disponibilidad Óptima',   'success'
