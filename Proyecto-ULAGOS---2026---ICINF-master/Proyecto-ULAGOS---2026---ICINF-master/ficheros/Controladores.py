"""
Controladores (rutas Flask).
Principio SRP: solo gestionan HTTP → llaman al servicio → devuelven respuesta.
Principio DIP: dependen de repositorios abstractos, no de modelos directamente.
"""
from flask import render_template, redirect, url_for, request, session, flash, jsonify
from functools import wraps
from datetime import datetime

from .configr import app, db
from .Modelos import User, Menu, Snack, Pedido, ahora_chile
from .repositories import (UserRepository, MenuRepository,
                            SnackRepository, PedidoRepository)
from .services import EventManager, StockObserver, PedidoService, estado_inventario

# ── Instancias de repositorios y servicios (inyección de dependencias) ────────
user_repo   = UserRepository()
menu_repo   = MenuRepository()
snack_repo  = SnackRepository()
pedido_repo = PedidoRepository()

event_mgr      = EventManager()
stock_observer = StockObserver(menu_repo, snack_repo)
event_mgr.subscribe('pedido_creado', stock_observer)

pedido_svc = PedidoService(pedido_repo, event_mgr)

# ── Helper de formato CLP ─────────────────────────────────────────────────────
def clp(n: int) -> str:
    return f'{n:,}'.replace(',', '.')

# ── Helper de formato Método de Pago ──────────────────────────────────────────
METODOS_PAGO = {
    'webpay_debito':  'Webpay · Débito',
    'webpay_credito': 'Webpay · Crédito',
    'junaeb_edenred':  'JUNAEB · Edenred',
}
def fmt_metodo(m: str) -> str:
    return METODOS_PAGO.get(m, m or 'No especificado')

# Exponemos estado_inventario al contexto Jinja global
app.jinja_env.globals['estado_inventario'] = estado_inventario
app.jinja_env.globals['clp'] = clp
app.jinja_env.globals['fmt_metodo'] = fmt_metodo

# ─────────────────────────────────────────────────────────────────────────────
#  DECORADORES
# ─────────────────────────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def dec(*args, **kwargs):
        if 'rut' not in session:
            flash('Debes iniciar sesión primero.', 'warning')
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return dec

def admin_required(f):
    @wraps(f)
    def dec(*args, **kwargs):
        if 'rut' not in session:
            flash('Debes iniciar sesión primero.', 'warning')
            return redirect(url_for('login_page'))
        if not session.get('role'):
            flash('Acceso restringido a administradores.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return dec

# ─────────────────────────────────────────────────────────────────────────────
#  AUTH
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/')
def login_page():
    if 'rut' in session:
        return redirect(url_for('admin') if session.get('role') else url_for('index'))
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    rut = request.form.get('rut', '').strip()
    pw  = request.form.get('password', '').strip()
    user = user_repo.authenticate(rut, pw)
    if user:
        session['rut']      = user.rut
        session['username'] = user.username
        session['role']     = bool(user.role)
        return redirect(url_for('admin') if user.role else url_for('index'))
    flash('RUT o contraseña incorrectos.', 'danger')
    return redirect(url_for('login_page'))

@app.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada correctamente.', 'info')
    return redirect(url_for('login_page'))

# ─────────────────────────────────────────────────────────────────────────────
#  VISTAS USUARIO
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/home')
@login_required
def index():
    return render_template('index.html')

@app.route('/almuerzos')
@login_required
def almuerzos():
    """Muestra el menú del día actual; si no existe, muestra todos los menús."""
    menu_hoy = menu_repo.get_today()
    todos    = menu_repo.get_all()
    return render_template('almuerzos.html', menu_hoy=menu_hoy, todos_menus=todos)

@app.route('/snacks')
@login_required
def snacks():
    return render_template('snacks.html', productos=snack_repo.get_as_dict())

# ─────────────────────────────────────────────────────────────────────────────
#  FLUJO DE COMPRA — ALMUERZO
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/pago')
@login_required
def pago():
    item    = request.args.get('item', 'Almuerzo')
    precio  = request.args.get('precio', 0, type=int)
    tipo    = request.args.get('tipo', 'almuerzo')
    menu_id = request.args.get('menu_id', type=int)
    field   = request.args.get('field', '')

    # Seguridad: solo se puede pagar el menú del día de HOY (ni admins ni
    # usuarios pueden reservar almuerzos de otros días de la semana).
    if tipo == 'almuerzo' and menu_id:
        menu_hoy = menu_repo.get_today()
        if not menu_hoy or menu_hoy.id != menu_id:
            flash('Solo puedes reservar el menú correspondiente al día de hoy.', 'danger')
            return redirect(url_for('almuerzos'))

    session['pago_item']    = item
    session['pago_precio']  = precio
    session['pago_tipo']    = tipo
    session['pago_menu_id'] = menu_id
    session['pago_field']   = field

    return render_template('pago.html',
                           item_nombre=item,
                           precio=precio,
                           precio_fmt=clp(precio),
                           tipo=tipo)

@app.route('/confirmar_pago', methods=['POST'])
@login_required
def confirmar_pago():
    metodo_pago    = request.form.get('metodo_pago', 'webpay_debito')
    carrito_snacks = session.pop('carrito_snacks', None)

    # ── Carrito de snacks (varios productos pagados juntos) ───────────────────
    if carrito_snacks:
        codigos = pedido_svc.registrar_multiples_snacks(session['rut'], carrito_snacks, metodo_pago)
        flash(f'¡Reserva confirmada! {len(codigos)} producto(s) registrado(s).', 'success')
        return redirect(url_for('reservas'))

    # ── Almuerzo individual ─────────────────────────────────────────────────
    item    = session.pop('pago_item',    'Almuerzo')
    precio  = session.pop('pago_precio',  0)
    menu_id = session.pop('pago_menu_id', None)
    field   = session.pop('pago_field',   None)

    # Re-validamos que el menú siga correspondiendo al día de hoy (por si la
    # página de pago quedó abierta y cambió el día mientras se pagaba).
    if menu_id:
        menu_hoy = menu_repo.get_today()
        if not menu_hoy or menu_hoy.id != menu_id:
            flash('Ese menú ya no corresponde al día de hoy. Por favor selecciona el menú actual.', 'danger')
            return redirect(url_for('almuerzos'))

    pedido = pedido_svc.registrar_almuerzo(
        session['rut'], item, precio, menu_id=menu_id, field=field, metodo_pago=metodo_pago
    )
    session['ultimo_codigo']  = pedido.codigo
    session['ultimo_item']    = item
    session['ultimo_metodo']  = fmt_metodo(metodo_pago)
    session['ultima_fecha']   = pedido.fecha.strftime('%d/%m/%Y')
    session['ultima_hora']    = pedido.fecha.strftime('%H:%M')
    return redirect(url_for('codigo_reserva'))

# ─────────────────────────────────────────────────────────────────────────────
#  FLUJO DE COMPRA — SNACKS (carrito → pasa por pago.html igual que almuerzos)
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/preparar_pago_snacks', methods=['POST'])
@login_required
def preparar_pago_snacks():
    """Recibe el carrito de snacks (JSON) y lo guarda en sesión para pagarlo
    en pago.html, igual que se hace con los almuerzos."""
    data  = request.get_json(silent=True) or {}
    items = data.get('items', [])
    if not items:
        return jsonify({'success': False, 'error': 'Tu reserva está vacía.'}), 400

    # Normalizamos cada item y completamos su snack_id real desde la BD
    # (necesario para poder descontar el stock correctamente al confirmar).
    snacks_por_nombre = {s.nombre: s.id for s in snack_repo.get_all()}
    carrito = []
    for it in items:
        nombre = it.get('name', 'Snack')
        carrito.append({
            'name':     nombre,
            'price':    int(it.get('price', 0)),
            'size':     it.get('size'),
            'snack_id': it.get('snack_id') or snacks_por_nombre.get(nombre),
        })

    session['carrito_snacks'] = carrito
    return jsonify({'success': True, 'redirect': url_for('pago_snacks')})

@app.route('/pago_snacks')
@login_required
def pago_snacks():
    carrito = session.get('carrito_snacks', [])
    if not carrito:
        flash('No tienes productos en tu reserva.', 'warning')
        return redirect(url_for('snacks'))

    total = sum(int(it.get('price', 0)) for it in carrito)
    return render_template('pago.html',
                           tipo='snack',
                           carrito=carrito,
                           item_nombre=f'{len(carrito)} producto(s) de Snacks',
                           precio=total,
                           precio_fmt=clp(total))

# ─────────────────────────────────────────────────────────────────────────────
#  CÓDIGO DE RESERVA Y MIS RESERVAS
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/codigo-reserva')
@login_required
def codigo_reserva():
    return render_template('codigo-reserva.html',
                           codigo    = session.get('ultimo_codigo', '---'),
                           item_nombre = session.get('ultimo_item', 'Pedido'),
                           metodo    = session.get('ultimo_metodo', 'No especificado'),
                           fecha     = session.get('ultima_fecha', ahora_chile().strftime('%d/%m/%Y')),
                           hora      = session.get('ultima_hora',  ahora_chile().strftime('%H:%M')))

@app.route('/reservas')
@login_required
def reservas():
    pedidos = pedido_repo.get_by_user(session['rut'])
    return render_template('reservas.html', pedidos=pedidos)

@app.route('/cancel_reservation/<int:id>')
@login_required
def cancel_reservation(id):
    pedido_svc.cancelar(id, session['rut'])
    flash('Pedido cancelado.', 'info')
    return redirect(url_for('reservas'))

# ─────────────────────────────────────────────────────────────────────────────
#  PANEL ADMINISTRACIÓN
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/admin')
@admin_required
def admin():
    stats   = pedido_repo.get_stats()
    menus   = menu_repo.get_all()
    snacks  = snack_repo.get_all()
    pedidos = pedido_repo.get_recent(20)

    # Inventario combinado (menus + snacks)
    inventario = []
    for m in menus:
        for p in m.to_platos():
            inventario.append({'name': f"{m.day.title()} – {p['label']}: {p['nombre']}", 'stock': p['stock']})
    for s in snacks:
        inventario.append({'name': s.nombre, 'stock': s.stock})

    return render_template('admin/admin.html',
        ventas_hoy         = clp(stats['ventas_hoy']),
        ventas_mes         = clp(stats['ventas_mes']),
        pedidos_pendientes = stats['pendientes'],
        pedidos_entregados = stats['entregados'],
        dinero_hoy         = clp(stats['ventas_hoy']),
        menus              = menus,
        snacks             = snacks,
        inventory          = inventario,
        pedidos_recientes  = pedidos,
    )

@app.route('/admin/pedido/<int:id>/entregar', methods=['POST'])
@admin_required
def entregar_pedido(id):
    p = pedido_svc.marcar_entregado(id)
    if p:
        flash(f'Pedido {p.codigo} marcado como entregado.', 'success')
    return redirect(url_for('admin'))

# ── Usuarios ──────────────────────────────────────────────────────────────────
@app.route('/admin/usuarios', methods=['GET', 'POST'])
@admin_required
def create_user():
    if request.method == 'POST':
        rut  = request.form.get('Rut', '').strip()
        pw   = request.form.get('password', '').strip()
        role = (request.form.get('role', 'user') == 'admin')
        if not rut or not pw:
            flash('RUT y contraseña son obligatorios.', 'warning')
        elif user_repo.exists(rut):
            flash(f'Ya existe un usuario con RUT {rut}.', 'warning')
        else:
            user_repo.save(User(rut=int(rut), username=rut, password=pw, role=role))
            flash(f'Usuario {rut} creado.', 'success')
    return render_template('admin/admin_users.html', users=user_repo.as_dict())

@app.route('/admin/usuarios/eliminar/<Rut>')
@admin_required
def delete_user(Rut):
    u = user_repo.get_by_id(int(Rut))
    if u:
        user_repo.delete(u)
        flash(f'Usuario {Rut} eliminado.', 'success')
    return redirect(url_for('create_user'))

# ── Menús ─────────────────────────────────────────────────────────────────────
@app.route('/admin/menu', methods=['GET', 'POST'])
@admin_required
def admin_menu():
    if request.method == 'POST':
        day  = request.form.get('day', '')
        time = f"{request.form.get('hour','12').zfill(2)}:{request.form.get('minute','00').zfill(2)}"

        def _int(k, d=0): return int(request.form.get(k, d) or d)

        existing = menu_repo.get_by_day(day)
        if existing:
            existing.time          = time
            existing.menu1         = request.form.get('menu1', '')
            existing.menu2         = request.form.get('menu2', '')
            existing.hipocalorico  = request.form.get('hipocalorico', '')
            existing.vegetariano   = request.form.get('vegetariano', '')
            existing.precio_menu1        = _int('precio_menu1', 4500)
            existing.precio_menu2        = _int('precio_menu2', 5200)
            existing.precio_hipocalorico = _int('precio_hipocalorico', 4200)
            existing.precio_vegetariano  = _int('precio_vegetariano', 4800)
            existing.stock_menu1         = _int('stock_menu1', 20)
            existing.stock_menu2         = _int('stock_menu2', 20)
            existing.stock_hipocalorico  = _int('stock_hipocalorico', 20)
            existing.stock_vegetariano   = _int('stock_vegetariano', 20)
            db.session.commit()
        else:
            nuevo = Menu(
                day=day, time=time,
                menu1=request.form.get('menu1',''), menu2=request.form.get('menu2',''),
                hipocalorico=request.form.get('hipocalorico',''), vegetariano=request.form.get('vegetariano',''),
                precio_menu1=_int('precio_menu1',4500), precio_menu2=_int('precio_menu2',5200),
                precio_hipocalorico=_int('precio_hipocalorico',4200), precio_vegetariano=_int('precio_vegetariano',4800),
                stock_menu1=_int('stock_menu1',20), stock_menu2=_int('stock_menu2',20),
                stock_hipocalorico=_int('stock_hipocalorico',20), stock_vegetariano=_int('stock_vegetariano',20),
            )
            menu_repo.save(nuevo)
        flash(f'Menú del {day.capitalize()} guardado.', 'success')

    return render_template('admin/admin_menu.html', menus=menu_repo.get_all())

@app.route('/admin/menu/get_menu/<day>')
@admin_required
def get_menu_by_day(day):
    return jsonify(menu_repo.to_json(menu_repo.get_by_day(day)))

@app.route('/admin/menu/eliminar/<int:id>')
@admin_required
def delete_menu(id):
    m = menu_repo.get_by_id(id)
    if m:
        menu_repo.delete(m)
        flash('Menú eliminado.', 'warning')
    return redirect(url_for('admin_menu'))

# ── Snacks ────────────────────────────────────────────────────────────────────
@app.route('/admin/snacks', methods=['GET', 'POST'])
@admin_required
def admin_snacks():
    edit_id      = request.args.get('edit_id', type=int)
    edit_product = snack_repo.get_by_id(edit_id) if edit_id else None

    if request.method == 'POST':
        pid  = request.form.get('product_id', type=int)
        data = dict(
            nombre        = request.form.get('nombre','').strip(),
            categoria     = request.form.get('category','').strip(),
            descripcion   = request.form.get('desc','').strip(),
            precio        = int(request.form.get('precio', 0) or 0),
            precio_grande = int(request.form.get('precio_grande') or 0) or None,
            stock         = int(request.form.get('stock', 0) or 0),
            img           = request.form.get('img','').strip(),
        )
        if pid:
            s = snack_repo.get_by_id(pid)
            if s:
                for k, v in data.items(): setattr(s, k, v)
                db.session.commit()
                flash(f'Producto "{s.nombre}" actualizado.', 'success')
        else:
            snack_repo.save(Snack(**data))
            flash(f'Producto "{data["nombre"]}" agregado.', 'success')
        return redirect(url_for('admin_snacks'))

    products = snack_repo.get_all()
    return render_template('admin/admin_snacks.html', products=products, edit_product=edit_product)

@app.route('/admin/snacks/eliminar/<int:product_id>', methods=['POST'])
@admin_required
def delete_snack(product_id):
    s = snack_repo.get_by_id(product_id)
    if s:
        snack_repo.delete(s)
        flash(f'"{s.nombre}" eliminado.', 'warning')
    return redirect(url_for('admin_snacks'))

@app.route('/admin/inventario/corregir')
@admin_required
def fix_inventory():
    flash('Inventario revisado.', 'success')
    return redirect(url_for('admin'))
