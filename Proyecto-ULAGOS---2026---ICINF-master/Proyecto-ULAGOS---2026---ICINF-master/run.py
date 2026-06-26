"""
Punto de entrada de la aplicación.
Al iniciar crea las tablas y puebla la BD con datos de ejemplo si está vacía.
"""
from ficheros.configr import app, db
from ficheros.Modelos import User, Snack, Menu
import ficheros.Controladores   # registra todas las rutas

# ─────────────────────────────────────────────────────────────────────────────
#  USUARIOS POR DEFECTO
# ─────────────────────────────────────────────────────────────────────────────
def seed_usuarios():
    if not User.query.filter_by(rut=12345678).first():
        db.session.add(User(rut=12345678, username='admin',      password='admin123', role=True))
        print("  ✔ Admin creado   → rut: 12345678 / pass: admin123")

    if not User.query.filter_by(rut=98765432).first():
        db.session.add(User(rut=98765432, username='estudiante', password='clave123', role=False))
        print("  ✔ Usuario creado → rut: 98765432 / pass: clave123")

    db.session.commit()

# ─────────────────────────────────────────────────────────────────────────────
#  ALMUERZOS POR DEFECTO (lunes a viernes)
# ─────────────────────────────────────────────────────────────────────────────
MENUS_INICIALES = [
    # day,        time,    menu1,                          menu2,                          hipocalorico,                       vegetariano
    ('lunes',     '12:30', 'Pollo asado con arroz',        'Carne mechada con puré',       'Ensalada de pollo y quínoa',       'Tofu salteado con verduras'),
    ('martes',    '12:30', 'Pavo al jugo con tallarines',  'Pescado frito con arroz',      'Ensalada César light',             'Garbanzos guisados con arroz integral'),
    ('miercoles', '12:30', 'Cazuela de vacuno',            'Charquicán con huevo frito',   'Ensalada de atún y verduras',      'Lentejas guisadas'),
    ('jueves',    '12:30', 'Pollo al curry con arroz',     'Lomo saltado',                 'Ensalada de pollo y palta',        'Hamburguesa de lentejas'),
    ('viernes',   '12:30', 'Filete de merluza al horno',   'Tallarines con salsa boloñesa','Ensalada mediterránea',            'Curry de garbanzos y verduras'),
]

def seed_menus():
    """
    Crea el almuerzo por defecto para cada día de lunes a viernes si ese día
    todavía no tiene un menú guardado (no sobrescribe los que ya existan,
    para no perder cambios hechos desde el panel de administración).
    """
    creados = 0
    for day, time, menu1, menu2, hipocalorico, vegetariano in MENUS_INICIALES:
        if Menu.query.filter_by(day=day).first():
            continue
        db.session.add(Menu(
            day=day, time=time,
            menu1=menu1, menu2=menu2,
            hipocalorico=hipocalorico, vegetariano=vegetariano,
        ))
        creados += 1
    if creados:
        db.session.commit()
        print(f"  ✔ {creados} almuerzo(s) por defecto creado(s) (lunes a viernes)")

# ─────────────────────────────────────────────────────────────────────────────
#  SNACKS POR DEFECTO
# ─────────────────────────────────────────────────────────────────────────────
SNACKS_INICIALES = [
    # (nombre, categoria, descripcion, precio, precio_grande, stock, img)
    ('Café Americano',    'cafes',      'Café negro suave preparado al momento.',                  1200, 1800, 50, 'https://images.unsplash.com/photo-1509042239860-f550ce710b93?w=400&auto=format&fit=crop'),
    ('Café con Leche',    'cafes',      'Espresso con leche caliente espumada.',                   1400, 2000, 40, 'https://images.unsplash.com/photo-1561882468-9110e03e0f78?w=400&auto=format&fit=crop'),
    ('Cappuccino',        'cafes',      'Espresso doble con leche vaporizada y espuma.',           1500, 2200, 35, 'https://images.unsplash.com/photo-1572442388796-11668a67e53d?w=400&auto=format&fit=crop'),
    ('Té Caliente',       'cafes',      'Negro, verde, menta o manzanilla a elección.',             900, 1300, 60, 'https://images.unsplash.com/photo-1544787219-7f47ccb76574?w=400&auto=format&fit=crop'),
    ('Sándwich de Ave',   'sandwiches', 'Pechuga a la plancha, lechuga, tomate y mayo.',           2500, None, 25, 'https://plus.unsplash.com/premium_photo-1700677185785-344e8ccdb99a?q=80&w=687&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D'),
    ('Sándwich Veggie',   'sandwiches', 'Palta, queso, champiñones y rúcula en pan integral.',    2800, None, 20, 'https://images.unsplash.com/photo-1520072959219-c595dc870360?w=400&auto=format&fit=crop'),
    ('Pan con huevo',      'sandwiches', 'Pan Fresco con huevos rvueltos.', 2200, None, 30, 'https://images.unsplash.com/photo-1733105666420-729679827ba1?q=80&w=1740&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D'),
    ('Muffin Arándano',   'reposteria', 'Esponjoso con arándanos frescos, horneado cada mañana.',1100, None, 45, 'https://images.unsplash.com/photo-1607958996333-41aef7caefaa?w=400&auto=format&fit=crop'),
    ('Torta de Chocolate', 'reposteria', 'Torta de chocolate artesanal.', 1300, None, 30, 'https://images.unsplash.com/photo-1517427294546-5aa121f68e8a?q=80&w=928&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D'),
    ('Brownie',           'reposteria', 'Chocolate intenso con nueces, denso y húmedo.',          1000, None, 50, 'https://images.unsplash.com/photo-1564355808539-22fda35bed7e?w=400&auto=format&fit=crop'),
    ('Empanada de Pino',  'snacks',     'Horneada con carne, cebolla, aceituna y huevo.',         1800, None, 40, 'https://images.unsplash.com/photo-1624128082323-beb6b8b508db?q=80&w=930&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D'),
    ('Papas Fritas',      'snacks',     'Crocantes con sal. ¡Perfectas para el recreo!',          1200, None, 35, 'https://images.unsplash.com/photo-1576107232684-1279f390859f?w=400&auto=format&fit=crop'),
    ('Fruta de Temporada','snacks',     'Mix de frutas frescas cortadas al momento.',             1000, None, 25, 'https://images.unsplash.com/photo-1490474418585-ba9bad8fd0ea?w=400&auto=format&fit=crop'),
    ('Agua Mineral',      'bebidas',    'Con gas, botella 500ml.',                                  1000, None,100, 'https://images.unsplash.com/photo-1638688569176-5b6db19f9d2a?q=80&w=687&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D'),
    ('Bebida en Lata',    'bebidas',    'Coca-Cola, Fanta o Sprite, 350ml fría.',                  1000, None, 80, 'https://images.unsplash.com/photo-1581098365948-6a5a912b7a49?q=80&w=1740&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D'),
    ('Jugo de Naranja',   'jugos',      'Naranja recién exprimida, sin azúcar. 300ml.',           1500, None, 30, 'https://images.unsplash.com/photo-1621506289937-a8e4df240d0b?w=400&auto=format&fit=crop'),
    ('Jugo de Manzana',   'jugos',      'Natural de manzana verde, sin conservantes.',            1400, None, 25, 'https://plus.unsplash.com/premium_photo-1724711441081-5c4199721ad7?q=80&w=687&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D'),
]

def seed_snacks():
    if Snack.query.count() > 0:
        return
    for nombre, cat, desc, precio, precio_grande, stock, img in SNACKS_INICIALES:
        db.session.add(Snack(
            nombre=nombre, categoria=cat, descripcion=desc,
            precio=precio, precio_grande=precio_grande,
            stock=stock, img=img,
        ))
    db.session.commit()
    print(f"  ✔ {len(SNACKS_INICIALES)} snacks cargados en BD")

def migrar_columna_metodo_pago():
    """
    Si la BD ya existía (creada antes de agregar el campo metodo_pago),
    SQLAlchemy.create_all() no modifica tablas ya creadas. Esta función
    agrega la columna 'metodo_pago' a la tabla 'pedido' si todavía no existe,
    para no perder los datos que ya estaban guardados.
    """
    from sqlalchemy import inspect, text
    inspector = inspect(db.engine)
    columnas = [c['name'] for c in inspector.get_columns('pedido')]
    if 'metodo_pago' not in columnas:
        with db.engine.begin() as conn:
            conn.execute(text(
                "ALTER TABLE pedido ADD COLUMN metodo_pago VARCHAR(40) DEFAULT 'No especificado'"
            ))
        print("  ✔ Columna 'metodo_pago' agregada a la tabla pedido (migración automática)")

# ─────────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("── Inicializando BD ──")
        migrar_columna_metodo_pago()
        seed_usuarios()
        seed_menus()
        seed_snacks()
        print("── Listo. Iniciando servidor... ──")
    app.run(debug=True)
