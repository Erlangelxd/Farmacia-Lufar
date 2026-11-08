-- ============================================================================
-- Farmacia Lufar — Script de creación de la base de datos (SQLite)
-- ============================================================================
--
-- Proyecto : Farmacia Lufar
-- Motor    : SQLite 3 (Django 6.1.1)
-- Alcance  : esquema completo del sistema (tablas de negocio + tablas Django).
--
-- IMPORTANTE
-- ----------
-- La vía canónica para crear la base de datos sigue siendo:
--
--     python manage.py migrate
--
-- Este script es una fotografía del esquema real generado por las migraciones
-- y sirve para documentación, revisión, auditoría o creación manual de una
-- base vacía. Si se ejecuta manualmente, después hay que poblar los permisos
-- de Django (por ejemplo con `python manage.py migrate --run-syncdb` o
-- `python manage.py sync_roles`), porque aquí solo se incluyen los datos
-- semilla mínimos (grupos y categoría General).
--
-- Uso:
--     sqlite3 db.sqlite3 < docs/script-creacion-bd.sql
--
-- Orden: primero las tablas independientes, luego las que dependen de ellas.
-- ============================================================================

PRAGMA foreign_keys = ON;

BEGIN TRANSACTION;

-- ============================================================================
-- 1. INFRAESTRUCTURA DE DJANGO
-- ============================================================================

CREATE TABLE "django_content_type" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "app_label" varchar(100) NOT NULL,
    "model" varchar(100) NOT NULL
);

CREATE TABLE "auth_group" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "name" varchar(150) NOT NULL UNIQUE
);

CREATE TABLE "auth_permission" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "content_type_id" integer NOT NULL REFERENCES "django_content_type" ("id")
        DEFERRABLE INITIALLY DEFERRED,
    "codename" varchar(100) NOT NULL,
    "name" varchar(255) NOT NULL
);

CREATE TABLE "auth_user" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "password" varchar(128) NOT NULL,
    "last_login" datetime NULL,
    "is_superuser" bool NOT NULL,
    "username" varchar(150) NOT NULL UNIQUE,
    "last_name" varchar(150) NOT NULL,
    "email" varchar(254) NOT NULL,
    "is_staff" bool NOT NULL,
    "is_active" bool NOT NULL,
    "date_joined" datetime NOT NULL,
    "first_name" varchar(150) NOT NULL
);

CREATE TABLE "auth_group_permissions" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "group_id" integer NOT NULL REFERENCES "auth_group" ("id")
        DEFERRABLE INITIALLY DEFERRED,
    "permission_id" integer NOT NULL REFERENCES "auth_permission" ("id")
        DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE "auth_user_groups" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "user_id" integer NOT NULL REFERENCES "auth_user" ("id")
        DEFERRABLE INITIALLY DEFERRED,
    "group_id" integer NOT NULL REFERENCES "auth_group" ("id")
        DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE "auth_user_user_permissions" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "user_id" integer NOT NULL REFERENCES "auth_user" ("id")
        DEFERRABLE INITIALLY DEFERRED,
    "permission_id" integer NOT NULL REFERENCES "auth_permission" ("id")
        DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE "django_admin_log" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "object_id" text NULL,
    "object_repr" varchar(200) NOT NULL,
    "action_flag" smallint unsigned NOT NULL CHECK ("action_flag" >= 0),
    "change_message" text NOT NULL,
    "content_type_id" integer NULL REFERENCES "django_content_type" ("id")
        DEFERRABLE INITIALLY DEFERRED,
    "user_id" integer NOT NULL REFERENCES "auth_user" ("id")
        DEFERRABLE INITIALLY DEFERRED,
    "action_time" datetime NOT NULL
);

CREATE TABLE "django_migrations" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "app" varchar(255) NOT NULL,
    "name" varchar(255) NOT NULL,
    "applied" datetime NOT NULL
);

CREATE TABLE "django_session" (
    "session_key" varchar(40) NOT NULL PRIMARY KEY,
    "session_data" text NOT NULL,
    "expire_date" datetime NOT NULL
);

-- ============================================================================
-- 2. MÓDULO CORE — CONFIGURACIÓN DEL SISTEMA
-- ============================================================================

CREATE TABLE "core_configuracionsistema" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "nombre_empresa" varchar(150) NOT NULL,
    "nit" varchar(30) NOT NULL,
    "direccion" varchar(200) NOT NULL,
    "telefono" varchar(30) NOT NULL,
    "email" varchar(254) NOT NULL,
    "moneda" varchar(10) NOT NULL,
    "impuesto_porcentaje" decimal NOT NULL,
    "logo" varchar(100) NOT NULL,
    "stock_minimo_default" integer unsigned NOT NULL
        CHECK ("stock_minimo_default" >= 0),
    "actualizado_en" datetime NOT NULL
);

-- ============================================================================
-- 3. MÓDULO CATÁLOGO
-- ============================================================================

CREATE TABLE "catalogo_categoria" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "nombre" varchar(80) NOT NULL UNIQUE,
    "descripcion" text NOT NULL,
    "activo" bool NOT NULL,
    "creado_en" datetime NOT NULL,
    "actualizado_en" datetime NOT NULL
);

CREATE TABLE "catalogo_formafarmaceutica" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "nombre" varchar(80) NOT NULL UNIQUE,
    "creado_en" datetime NOT NULL,
    "actualizado_en" datetime NOT NULL
);

CREATE TABLE "catalogo_laboratorio" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "nombre" varchar(120) NOT NULL UNIQUE,
    "pais" varchar(80) NOT NULL,
    "activo" bool NOT NULL,
    "creado_en" datetime NOT NULL,
    "actualizado_en" datetime NOT NULL
);

CREATE TABLE "catalogo_presentacion" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "nombre" varchar(80) NOT NULL UNIQUE,
    "creado_en" datetime NOT NULL,
    "actualizado_en" datetime NOT NULL
);

CREATE TABLE "catalogo_producto" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "codigo" varchar(30) NOT NULL UNIQUE,
    "nombre" varchar(150) NOT NULL,
    "precio_venta" decimal NOT NULL,
    "activo" bool NOT NULL,
    "creado_en" datetime NOT NULL,
    "actualizado_en" datetime NOT NULL,
    "concentracion" varchar(80) NOT NULL,
    "descripcion" text NOT NULL,
    "principio_activo" varchar(150) NOT NULL,
    "stock_minimo" integer unsigned NOT NULL CHECK ("stock_minimo" >= 0),
    "unidad_medida" varchar(30) NOT NULL,
    "categoria_id" bigint NOT NULL REFERENCES "catalogo_categoria" ("id")
        DEFERRABLE INITIALLY DEFERRED,
    "forma_farmaceutica_id" bigint NULL REFERENCES "catalogo_formafarmaceutica" ("id")
        DEFERRABLE INITIALLY DEFERRED,
    "laboratorio_id" bigint NULL REFERENCES "catalogo_laboratorio" ("id")
        DEFERRABLE INITIALLY DEFERRED,
    "presentacion_id" bigint NULL REFERENCES "catalogo_presentacion" ("id")
        DEFERRABLE INITIALLY DEFERRED,
    CONSTRAINT "catalogo_producto_precio_no_negativo" CHECK ("precio_venta" >= '0'),
    CONSTRAINT "catalogo_producto_stock_minimo_no_negativo" CHECK ("stock_minimo" >= 0)
);

-- ============================================================================
-- 4. MÓDULO CLIENTES
-- ============================================================================

CREATE TABLE "clientes_cliente" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "nombre" varchar(150) NOT NULL,
    "tipo_documento" varchar(20) NOT NULL,
    "numero_documento" varchar(30) NOT NULL,
    "telefono" varchar(30) NOT NULL,
    "activo" bool NOT NULL,
    "creado_en" datetime NOT NULL,
    "actualizado_en" datetime NOT NULL,
    "creado_por_id" integer NULL REFERENCES "auth_user" ("id")
        DEFERRABLE INITIALLY DEFERRED,
    CONSTRAINT "clientes_documento_tipo_numero_coherentes" CHECK (
        (("numero_documento" = '' AND "tipo_documento" = '')
         OR (NOT ("tipo_documento" = '') AND NOT ("numero_documento" = '')))
    )
);

-- ============================================================================
-- 5. MÓDULO COMPRAS — PROVEEDORES Y COMPRAS
-- ============================================================================

CREATE TABLE "compras_proveedor" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "nombre" varchar(150) NOT NULL,
    "nit" varchar(30) NOT NULL,
    "telefono" varchar(30) NOT NULL,
    "email" varchar(254) NOT NULL,
    "direccion" varchar(200) NOT NULL,
    "contacto" varchar(120) NOT NULL,
    "activo" bool NOT NULL,
    "creado_en" datetime NOT NULL,
    "actualizado_en" datetime NOT NULL
);

CREATE TABLE "compras_compra" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "numero_factura" varchar(50) NOT NULL,
    "fecha_compra" date NOT NULL,
    "fecha_recepcion" date NULL,
    "estado" varchar(10) NOT NULL,
    "subtotal" decimal NOT NULL,
    "impuesto" decimal NOT NULL,
    "total" decimal NOT NULL,
    "observaciones" text NOT NULL,
    "creado_en" datetime NOT NULL,
    "actualizado_en" datetime NOT NULL,
    "usuario_id" integer NOT NULL REFERENCES "auth_user" ("id")
        DEFERRABLE INITIALLY DEFERRED,
    "proveedor_id" bigint NOT NULL REFERENCES "compras_proveedor" ("id")
        DEFERRABLE INITIALLY DEFERRED,
    CONSTRAINT "compras_compra_subtotal_no_negativo" CHECK ("subtotal" >= '0'),
    CONSTRAINT "compras_compra_impuesto_no_negativo" CHECK ("impuesto" >= '0'),
    CONSTRAINT "compras_compra_total_no_negativo" CHECK ("total" >= '0')
);

-- ============================================================================
-- 6. MÓDULO INVENTARIO — LOTES
-- ============================================================================

CREATE TABLE "inventario_lote" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "codigo_lote" varchar(50) NOT NULL,
    "fecha_fabricacion" date NULL,
    "fecha_vencimiento" date NULL,
    "fecha_ingreso" date NOT NULL,
    "stock_actual" decimal NOT NULL,
    "activo" bool NOT NULL,
    "creado_en" datetime NOT NULL,
    "actualizado_en" datetime NOT NULL,
    "producto_id" bigint NOT NULL REFERENCES "catalogo_producto" ("id")
        DEFERRABLE INITIALLY DEFERRED,
    CONSTRAINT "inventario_lote_unico_por_producto" UNIQUE ("producto_id", "codigo_lote"),
    CONSTRAINT "inventario_lote_stock_no_negativo" CHECK ("stock_actual" >= '0')
);

-- Detalle de compra: depende de compra, producto y lote.
CREATE TABLE "compras_detallecompra" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "cantidad" integer unsigned NOT NULL CHECK ("cantidad" >= 0),
    "costo_unitario" decimal NOT NULL,
    "subtotal" decimal NOT NULL,
    "compra_id" bigint NOT NULL REFERENCES "compras_compra" ("id")
        DEFERRABLE INITIALLY DEFERRED,
    "lote_id" bigint NULL REFERENCES "inventario_lote" ("id")
        DEFERRABLE INITIALLY DEFERRED,
    "producto_id" bigint NOT NULL REFERENCES "catalogo_producto" ("id")
        DEFERRABLE INITIALLY DEFERRED,
    CONSTRAINT "compras_detalle_cantidad_positiva" CHECK ("cantidad" > 0),
    CONSTRAINT "compras_detalle_costo_no_negativo" CHECK ("costo_unitario" >= '0'),
    CONSTRAINT "compras_detalle_subtotal_no_negativo" CHECK ("subtotal" >= '0')
);

-- ============================================================================
-- 7. MÓDULO VENTAS
-- ============================================================================

CREATE TABLE "ventas_venta" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "metodo_pago" varchar(20) NOT NULL,
    "monto_recibido" decimal NOT NULL,
    "total" decimal NOT NULL,
    "creado_en" datetime NOT NULL,
    "cliente_id" bigint NULL REFERENCES "clientes_cliente" ("id")
        DEFERRABLE INITIALLY DEFERRED,
    "vendedor_id" integer NOT NULL REFERENCES "auth_user" ("id")
        DEFERRABLE INITIALLY DEFERRED,
    CONSTRAINT "ventas_total_no_negativo" CHECK ("total" >= '0'),
    CONSTRAINT "ventas_monto_recibido_no_negativo" CHECK ("monto_recibido" >= '0'),
    CONSTRAINT "ventas_monto_recibido_cubre_total" CHECK ("monto_recibido" >= ("total"))
);

CREATE TABLE "ventas_detalleventa" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "codigo_producto" varchar(30) NOT NULL,
    "nombre_producto" varchar(150) NOT NULL,
    "cantidad" integer unsigned NOT NULL CHECK ("cantidad" >= 0),
    "precio_unitario" decimal NOT NULL,
    "creado_en" datetime NOT NULL,
    "producto_id" bigint NOT NULL REFERENCES "catalogo_producto" ("id")
        DEFERRABLE INITIALLY DEFERRED,
    "venta_id" bigint NOT NULL REFERENCES "ventas_venta" ("id")
        DEFERRABLE INITIALLY DEFERRED,
    "costo_total" decimal NULL,
    CONSTRAINT "ventas_detalle_cantidad_positiva" CHECK ("cantidad" > 0),
    CONSTRAINT "ventas_detalle_precio_no_negativo" CHECK ("precio_unitario" >= '0'),
    CONSTRAINT "ventas_detalle_producto_unico_por_venta" UNIQUE ("venta_id", "producto_id")
);

-- ============================================================================
-- 8. MÓDULO INVENTARIO — MOVIMIENTOS Y COSTOS
-- ============================================================================

CREATE TABLE "inventario_movimientoinventario" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "tipo" varchar(20) NOT NULL,
    "cantidad" decimal NOT NULL,
    "stock_resultante" decimal NOT NULL,
    "motivo" varchar(200) NOT NULL,
    "fecha" datetime NOT NULL,
    "detalle_venta_id" bigint NULL REFERENCES "ventas_detalleventa" ("id")
        DEFERRABLE INITIALLY DEFERRED,
    "lote_id" bigint NOT NULL REFERENCES "inventario_lote" ("id")
        DEFERRABLE INITIALLY DEFERRED,
    "usuario_id" integer NOT NULL REFERENCES "auth_user" ("id")
        DEFERRABLE INITIALLY DEFERRED,
    "costo_total" decimal NULL,
    CONSTRAINT "inventario_mov_cantidad_positiva" CHECK ("cantidad" > 0),
    CONSTRAINT "inventario_mov_stock_no_negativo" CHECK ("stock_resultante" >= '0')
);

CREATE TABLE "inventario_capacosto" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "cantidad_inicial" decimal NOT NULL,
    "cantidad_restante" decimal NOT NULL,
    "costo_unitario" decimal NULL,
    "creado_en" datetime NOT NULL,
    "lote_id" bigint NOT NULL REFERENCES "inventario_lote" ("id")
        DEFERRABLE INITIALLY DEFERRED,
    "movimiento_entrada_id" bigint NULL UNIQUE REFERENCES "inventario_movimientoinventario" ("id")
        DEFERRABLE INITIALLY DEFERRED,
    CONSTRAINT "inventario_capa_cantidad_inicial_positiva" CHECK ("cantidad_inicial" > '0'),
    CONSTRAINT "inventario_capa_cantidad_restante_valida" CHECK (
        ("cantidad_restante" >= '0' AND "cantidad_restante" <= ("cantidad_inicial"))
    )
);

CREATE TABLE "inventario_asignacioncostoinventario" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "cantidad" decimal NOT NULL,
    "costo_unitario" decimal NULL,
    "movimiento_id" bigint NOT NULL REFERENCES "inventario_movimientoinventario" ("id")
        DEFERRABLE INITIALLY DEFERRED,
    "capa_id" bigint NOT NULL REFERENCES "inventario_capacosto" ("id")
        DEFERRABLE INITIALLY DEFERRED,
    CONSTRAINT "inventario_asignacion_cantidad_positiva" CHECK ("cantidad" > '0'),
    CONSTRAINT "inventario_asignacion_movimiento_capa_unica" UNIQUE ("movimiento_id", "capa_id")
);

CREATE TABLE "inventario_ajustecostoinventario" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "cantidad" decimal NOT NULL,
    "costo_unitario" decimal NOT NULL,
    "motivo" varchar(200) NOT NULL,
    "fecha" datetime NOT NULL,
    "lote_id" bigint NOT NULL REFERENCES "inventario_lote" ("id")
        DEFERRABLE INITIALLY DEFERRED,
    "usuario_id" integer NOT NULL REFERENCES "auth_user" ("id")
        DEFERRABLE INITIALLY DEFERRED
);

-- ============================================================================
-- 9. ÍNDICES
-- ============================================================================

-- Django: autenticación y sesiones
CREATE INDEX "auth_group_permissions_group_id_b120cbf9"
    ON "auth_group_permissions" ("group_id");
CREATE UNIQUE INDEX "auth_group_permissions_group_id_permission_id_0cd325b0_uniq"
    ON "auth_group_permissions" ("group_id", "permission_id");
CREATE INDEX "auth_group_permissions_permission_id_84c5c92e"
    ON "auth_group_permissions" ("permission_id");
CREATE INDEX "auth_permission_content_type_id_2f476e4b"
    ON "auth_permission" ("content_type_id");
CREATE UNIQUE INDEX "auth_permission_content_type_id_codename_01ab375a_uniq"
    ON "auth_permission" ("content_type_id", "codename");
CREATE INDEX "auth_user_groups_group_id_97559544"
    ON "auth_user_groups" ("group_id");
CREATE INDEX "auth_user_groups_user_id_6a12ed8b"
    ON "auth_user_groups" ("user_id");
CREATE UNIQUE INDEX "auth_user_groups_user_id_group_id_94350c0c_uniq"
    ON "auth_user_groups" ("user_id", "group_id");
CREATE INDEX "auth_user_user_permissions_permission_id_1fbb5f2c"
    ON "auth_user_user_permissions" ("permission_id");
CREATE INDEX "auth_user_user_permissions_user_id_a95ead1b"
    ON "auth_user_user_permissions" ("user_id");
CREATE UNIQUE INDEX "auth_user_user_permissions_user_id_permission_id_14a6b632_uniq"
    ON "auth_user_user_permissions" ("user_id", "permission_id");
CREATE INDEX "django_admin_log_content_type_id_c4bce8eb"
    ON "django_admin_log" ("content_type_id");
CREATE INDEX "django_admin_log_user_id_c564eba6"
    ON "django_admin_log" ("user_id");
CREATE UNIQUE INDEX "django_content_type_app_label_model_76bd3d3b_uniq"
    ON "django_content_type" ("app_label", "model");
CREATE INDEX "django_session_expire_date_a5c62663"
    ON "django_session" ("expire_date");

-- Catálogo
CREATE INDEX "catalogo_producto_categoria_id_19eecf17"
    ON "catalogo_producto" ("categoria_id");
CREATE INDEX "catalogo_producto_forma_farmaceutica_id_3dc8c3f0"
    ON "catalogo_producto" ("forma_farmaceutica_id");
CREATE INDEX "catalogo_producto_laboratorio_id_08ed6ad0"
    ON "catalogo_producto" ("laboratorio_id");
CREATE INDEX "catalogo_producto_nombre_idx"
    ON "catalogo_producto" ("nombre");
CREATE INDEX "catalogo_producto_presentacion_id_aa884cbc"
    ON "catalogo_producto" ("presentacion_id");

-- Clientes
CREATE INDEX "clientes_cliente_creado_por_id_3b48e22c"
    ON "clientes_cliente" ("creado_por_id");
CREATE UNIQUE INDEX "clientes_documento_unico_por_tipo"
    ON "clientes_cliente" ("tipo_documento", "numero_documento")
    WHERE (NOT ("numero_documento" = '') AND NOT ("tipo_documento" = ''));

-- Compras
CREATE INDEX "compras_compra_estado_idx"
    ON "compras_compra" ("estado");
CREATE INDEX "compras_compra_fecha_idx"
    ON "compras_compra" ("fecha_compra");
CREATE INDEX "compras_compra_proveedor_id_d647dfa3"
    ON "compras_compra" ("proveedor_id");
CREATE INDEX "compras_compra_usuario_id_833384c6"
    ON "compras_compra" ("usuario_id");
CREATE INDEX "compras_detallecompra_compra_id_9d6236ea"
    ON "compras_detallecompra" ("compra_id");
CREATE INDEX "compras_detallecompra_lote_id_b4576aa7"
    ON "compras_detallecompra" ("lote_id");
CREATE INDEX "compras_detallecompra_producto_id_38c7f9c4"
    ON "compras_detallecompra" ("producto_id");
CREATE UNIQUE INDEX "compras_proveedor_nit_unico"
    ON "compras_proveedor" ("nit")
    WHERE NOT ("nit" = '');

-- Inventario
CREATE INDEX "inventario_ajustecostoinventario_lote_id_34df33c7"
    ON "inventario_ajustecostoinventario" ("lote_id");
CREATE INDEX "inventario_ajustecostoinventario_usuario_id_fc04dd6b"
    ON "inventario_ajustecostoinventario" ("usuario_id");
CREATE INDEX "inventario_asignacioncostoinventario_capa_id_77cadffb"
    ON "inventario_asignacioncostoinventario" ("capa_id");
CREATE INDEX "inventario_asignacioncostoinventario_movimiento_id_676535f9"
    ON "inventario_asignacioncostoinventario" ("movimiento_id");
CREATE INDEX "inventario_capacosto_lote_id_0e449035"
    ON "inventario_capacosto" ("lote_id");
CREATE INDEX "inventario_lote_prod_venc_idx"
    ON "inventario_lote" ("producto_id", "fecha_vencimiento");
CREATE INDEX "inventario_lote_producto_id_339cfe1f"
    ON "inventario_lote" ("producto_id");
CREATE INDEX "inventario_mov_fecha_idx"
    ON "inventario_movimientoinventario" ("fecha");
CREATE INDEX "inventario_mov_lote_fecha_idx"
    ON "inventario_movimientoinventario" ("lote_id", "fecha");
CREATE INDEX "inventario_movimientoinventario_detalle_venta_id_efe044e4"
    ON "inventario_movimientoinventario" ("detalle_venta_id");
CREATE INDEX "inventario_movimientoinventario_lote_id_45a552d7"
    ON "inventario_movimientoinventario" ("lote_id");
CREATE INDEX "inventario_movimientoinventario_usuario_id_6ba25fdb"
    ON "inventario_movimientoinventario" ("usuario_id");

-- Ventas
CREATE INDEX "ventas_detalleventa_producto_id_a820c807"
    ON "ventas_detalleventa" ("producto_id");
CREATE INDEX "ventas_detalleventa_venta_id_c370bcd7"
    ON "ventas_detalleventa" ("venta_id");
CREATE INDEX "ventas_venta_cliente_id_85f33a80"
    ON "ventas_venta" ("cliente_id");
CREATE INDEX "ventas_venta_vendedor_id_2f6b0d76"
    ON "ventas_venta" ("vendedor_id");

-- ============================================================================
-- 10. DATOS SEMILLA
-- ============================================================================
-- Los permisos de Django (auth_permission) y su asignación a los grupos se
-- generan con `python manage.py migrate` / `python manage.py sync_roles`.
-- Aquí solo se crean los registros que las migraciones de datos dejan fijos.

INSERT INTO "auth_group" ("name") VALUES ('Administrador');
INSERT INTO "auth_group" ("name") VALUES ('Vendedor');

INSERT INTO "catalogo_categoria" (
    "nombre", "descripcion", "activo", "creado_en", "actualizado_en"
) VALUES (
    'General',
    'Categoría asignada por defecto.',
    1,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);

-- Configuración inicial opcional (una sola fila lógica, pk = 1).
-- Descomenta si se desea arrancar con datos de la farmacia.
-- INSERT INTO "core_configuracionsistema" (
--     "id", "nombre_empresa", "nit", "direccion", "telefono", "email",
--     "moneda", "impuesto_porcentaje", "logo", "stock_minimo_default",
--     "actualizado_en"
-- ) VALUES (
--     1, 'Farmacia Lufar', '', '', '', '', 'BOB', 0.00, '', 5,
--     CURRENT_TIMESTAMP
-- );

COMMIT;
