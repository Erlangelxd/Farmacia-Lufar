# Diccionario de datos — Farmacia Lufar

Documento de referencia del esquema físico de la base de datos del sistema.
Describe cada tabla de negocio, sus columnas, tipos, nulabilidad, valores
predeterminados, claves y restricciones, además de las reglas de negocio que
no se pueden expresar solo con DDL.

| Dato | Valor |
|---|---|
| Proyecto | Farmacia Lufar |
| Motor | SQLite 3 |
| Framework | Django 6.1.1 |
| Base de datos | `db.sqlite3` |
| Esquema | Generado por las migraciones de Django |
| Documento SQL | [`script-creacion-bd.sql`](script-creacion-bd.sql) |
| Modelo ER | [`modelo-er-relacional.tex`](modelo-er-relacional.tex) |
| Fecha de corte | Noviembre de 2026 |

> **Fuente de verdad:** las migraciones y los modelos del código. Este
> diccionario y el script SQL son una fotografía del esquema; si cambia un
> modelo, se debe crear una migración nueva y actualizar ambos documentos.

## 1. Cómo se genera la base de datos

La vía oficial es:

```bash
python manage.py migrate
```

El script [`script-creacion-bd.sql`](script-creacion-bd.sql) reproduce el mismo
esquema sobre una base vacía:

```bash
sqlite3 db.sqlite3 < docs/script-creacion-bd.sql
```

Después de ejecutarlo manualmente hay que regenerar los permisos de Django y
sincronizar los roles:

```bash
python manage.py migrate
python manage.py sync_roles
```

## 2. Convenciones

### 2.1 Tipos

SQLite usa afinidad de tipos; Django declara el tipo lógico en el DDL.

| Tipo declarado | Uso en el proyecto |
|---|---|
| `integer` / `bigint` | Claves primarias y foráneas. |
| `integer unsigned` | Enteros no negativos (`cantidad`, `stock_minimo`). |
| `bool` | Valores `0` o `1`. |
| `varchar(n)` | Texto de longitud limitada. |
| `text` | Texto libre. |
| `decimal` | Numérico con precisión definida por Django; SQLite no la impone. |
| `date` | Fecha `YYYY-MM-DD`. |
| `datetime` | Fecha y hora `YYYY-MM-DD HH:MM:SS`. |

### 2.2 Nulabilidad y valores vacíos

- `NULL` solo aparece donde el modelo usa `null=True`.
- Los campos de texto con `blank=True` son `NOT NULL` en la base y usan la
  cadena vacía `''` como valor por defecto. La validación de "vacío" se hace en
  formularios y modelos.
- Las claves foráneas opcionales sí admiten `NULL`.

### 2.3 Claves y relaciones

- Toda tabla de negocio usa `id` entero autoincremental como clave primaria.
- Las claves foráneas se nombran `<entidad>_id`.
- `PROTECT` impide borrar un registro referenciado; `CASCADE` elimina los
  hijos; `SET NULL` deja la referencia vacía.
- Los borrados físicos están deshabilitados en la interfaz para las entidades
  de negocio; se usa el campo `activo` cuando existe.

### 2.4 Fechas

- `creado_en`, `actualizado_en` y `fecha` se generan automáticamente.
- `fecha_ingreso` y `fecha_compra` usan la fecha local del servidor
  (`America/La_Paz` por defecto).
- Las fechas de vencimiento son opcionales, pero si existen se usan para FEFO
  (primero en vencer, primero en salir).

## 3. Resumen de tablas

| Módulo | Tabla | Propósito |
|---|---|---|
| `core` | `core_configuracionsistema` | Datos generales de la farmacia. |
| `catalogo` | `catalogo_categoria` | Clasificación de productos. |
| `catalogo` | `catalogo_laboratorio` | Laboratorios fabricantes. |
| `catalogo` | `catalogo_formafarmaceutica` | Formas farmacéuticas. |
| `catalogo` | `catalogo_presentacion` | Presentaciones comerciales. |
| `catalogo` | `catalogo_producto` | Productos y precios de venta. |
| `clientes` | `clientes_cliente` | Clientes de la farmacia. |
| `compras` | `compras_proveedor` | Proveedores. |
| `compras` | `compras_compra` | Documento de compra. |
| `compras` | `compras_detallecompra` | Líneas de la compra. |
| `inventario` | `inventario_lote` | Lotes y existencias. |
| `inventario` | `inventario_movimientoinventario` | Movimientos de stock. |
| `inventario` | `inventario_capacosto` | Capas de costo por lote. |
| `inventario` | `inventario_asignacioncostoinventario` | Consumo de capas por salida. |
| `inventario` | `inventario_ajustecostoinventario` | Auditoría de costos heredados. |
| `ventas` | `ventas_venta` | Cabecera de venta. |
| `ventas` | `ventas_detalleventa` | Líneas de venta. |
| Django | `auth_*`, `django_*` | Usuarios, grupos, permisos, sesiones y migraciones. |

Total: **17 tablas de negocio** y **10 tablas de infraestructura Django**.

## 4. Módulo `core`

### 4.1 `core_configuracionsistema`

Configuración general de la farmacia. El modelo fuerza una sola fila lógica con
`pk = 1`.

| Columna | Tipo | Nulo | Predeterminado | Clave / restricción | Descripción |
|---|---|---|---|---|---|
| `id` | `bigint` | No | Autoincremental | PK | Identificador. |
| `nombre_empresa` | `varchar(150)` | No | `Farmacia Lufar` | — | Nombre comercial. |
| `nit` | `varchar(30)` | No | `''` | — | NIT, normalizado a mayúsculas. |
| `direccion` | `varchar(200)` | No | `''` | — | Dirección. |
| `telefono` | `varchar(30)` | No | `''` | — | Teléfono. |
| `email` | `varchar(254)` | No | `''` | — | Correo electrónico. |
| `moneda` | `varchar(10)` | No | `BOB` | — | Moneda del sistema. |
| `impuesto_porcentaje` | `decimal(5,2)` | No | `0.00` | `>= 0` | Porcentaje de impuesto. |
| `logo` | `varchar(100)` | No | `''` | — | Ruta del logotipo en `media/configuracion/`. |
| `stock_minimo_default` | `integer unsigned` | No | `5` | `>= 0` | Umbral sugerido para productos nuevos. |
| `actualizado_en` | `datetime` | No | Automático | — | Última actualización. |

## 5. Módulo `catalogo`

### 5.1 `catalogo_categoria`

| Columna | Tipo | Nulo | Predeterminado | Clave / restricción | Descripción |
|---|---|---|---|---|---|
| `id` | `bigint` | No | Autoincremental | PK | Identificador. |
| `nombre` | `varchar(80)` | No | — | UNIQUE | Nombre de la categoría. |
| `descripcion` | `text` | No | `''` | — | Descripción libre. |
| `activo` | `bool` | No | `1` | — | Indica si está disponible. |
| `creado_en` | `datetime` | No | Automático | — | Fecha de registro. |
| `actualizado_en` | `datetime` | No | Automático | — | Última actualización. |

Reglas:

- El nombre se compara sin distinguir mayúsculas en la capa de aplicación.
- No se puede desactivar una categoría con productos activos.
- La migración `catalogo.0003_categoria_general` crea la categoría `General`.

### 5.2 `catalogo_laboratorio`

| Columna | Tipo | Nulo | Predeterminado | Clave / restricción | Descripción |
|---|---|---|---|---|---|
| `id` | `bigint` | No | Autoincremental | PK | Identificador. |
| `nombre` | `varchar(120)` | No | — | UNIQUE | Nombre del laboratorio. |
| `pais` | `varchar(80)` | No | `''` | — | País de origen. |
| `activo` | `bool` | No | `1` | — | Disponible para nuevos productos. |
| `creado_en` | `datetime` | No | Automático | — | Fecha de registro. |
| `actualizado_en` | `datetime` | No | Automático | — | Última actualización. |

### 5.3 `catalogo_formafarmaceutica`

| Columna | Tipo | Nulo | Predeterminado | Clave / restricción | Descripción |
|---|---|---|---|---|---|
| `id` | `bigint` | No | Autoincremental | PK | Identificador. |
| `nombre` | `varchar(80)` | No | — | UNIQUE | Forma farmacéutica (tableta, jarabe, etc.). |
| `creado_en` | `datetime` | No | Automático | — | Fecha de registro. |
| `actualizado_en` | `datetime` | No | Automático | — | Última actualización. |

### 5.4 `catalogo_presentacion`

| Columna | Tipo | Nulo | Predeterminado | Clave / restricción | Descripción |
|---|---|---|---|---|---|
| `id` | `bigint` | No | Autoincremental | PK | Identificador. |
| `nombre` | `varchar(80)` | No | — | UNIQUE | Presentación comercial (caja, frasco, etc.). |
| `creado_en` | `datetime` | No | Automático | — | Fecha de registro. |
| `actualizado_en` | `datetime` | No | Automático | — | Última actualización. |

### 5.5 `catalogo_producto`

Producto comercializable. **No almacena stock**: las existencias viven en
`inventario_lote`.

| Columna | Tipo | Nulo | Predeterminado | Clave / restricción | Descripción |
|---|---|---|---|---|---|
| `id` | `bigint` | No | Autoincremental | PK | Identificador. |
| `codigo` | `varchar(30)` | No | — | UNIQUE | Código interno, normalizado a mayúsculas. |
| `nombre` | `varchar(150)` | No | — | — | Nombre comercial. |
| `descripcion` | `text` | No | `''` | — | Descripción libre. |
| `principio_activo` | `varchar(150)` | No | `''` | — | Principio activo. |
| `categoria_id` | `bigint` | No | `General` | FK → `catalogo_categoria.id` (PROTECT) | Categoría. |
| `laboratorio_id` | `bigint` | Sí | `NULL` | FK → `catalogo_laboratorio.id` (PROTECT) | Laboratorio. |
| `forma_farmaceutica_id` | `bigint` | Sí | `NULL` | FK → `catalogo_formafarmaceutica.id` (PROTECT) | Forma farmacéutica. |
| `presentacion_id` | `bigint` | Sí | `NULL` | FK → `catalogo_presentacion.id` (PROTECT) | Presentación. |
| `concentracion` | `varchar(80)` | No | `''` | — | Concentración (por ejemplo `500 mg`). |
| `unidad_medida` | `varchar(30)` | No | `UNIDAD` | — | Unidad de venta. |
| `precio_venta` | `decimal(10,2)` | No | — | `>= 0` | Precio unitario de venta. |
| `stock_minimo` | `integer unsigned` | No | `0` | `>= 0` | Umbral de alerta de reposición. |
| `activo` | `bool` | No | `1` | — | Producto disponible. |
| `creado_en` | `datetime` | No | Automático | — | Fecha de registro. |
| `actualizado_en` | `datetime` | No | Automático | — | Última actualización. |

Índices: `catalogo_producto_nombre_idx`, `catalogo_producto_categoria_id_19eecf17`,
`catalogo_producto_laboratorio_id_08ed6ad0`,
`catalogo_producto_forma_farmaceutica_id_3dc8c3f0`,
`catalogo_producto_presentacion_id_aa884cbc`.

## 6. Módulo `clientes`

### 6.1 `clientes_cliente`

| Columna | Tipo | Nulo | Predeterminado | Clave / restricción | Descripción |
|---|---|---|---|---|---|
| `id` | `bigint` | No | Autoincremental | PK | Identificador. |
| `nombre` | `varchar(150)` | No | — | — | Nombre completo o razón social. |
| `tipo_documento` | `varchar(20)` | No | `''` | Enum `CI`, `NIT`, `PASAPORTE`, `OTRO` | Tipo de documento. |
| `numero_documento` | `varchar(30)` | No | `''` | — | Número de documento. |
| `telefono` | `varchar(30)` | No | `''` | — | Teléfono de contacto. |
| `activo` | `bool` | No | `1` | — | Cliente habilitado. |
| `creado_por_id` | `integer` | Sí | `NULL` | FK → `auth_user.id` (SET NULL) | Usuario que registró el cliente. |
| `creado_en` | `datetime` | No | Automático | — | Fecha de registro. |
| `actualizado_en` | `datetime` | No | Automático | — | Última actualización. |

Restricciones:

- `clientes_documento_tipo_numero_coherentes`: tipo y número deben estar ambos
  vacíos o ambos presentes.
- `clientes_documento_unico_por_tipo`: índice único parcial sobre
  (`tipo_documento`, `numero_documento`) cuando ambos no están vacíos.
- No existen campos de correo ni dirección en esta etapa.

## 7. Módulo `compras`

### 7.1 `compras_proveedor`

| Columna | Tipo | Nulo | Predeterminado | Clave / restricción | Descripción |
|---|---|---|---|---|---|
| `id` | `bigint` | No | Autoincremental | PK | Identificador. |
| `nombre` | `varchar(150)` | No | — | — | Nombre o razón social. |
| `nit` | `varchar(30)` | No | `''` | UNIQUE parcial | NIT, normalizado a mayúsculas. |
| `telefono` | `varchar(30)` | No | `''` | — | Teléfono. |
| `email` | `varchar(254)` | No | `''` | — | Correo electrónico. |
| `direccion` | `varchar(200)` | No | `''` | — | Dirección. |
| `contacto` | `varchar(120)` | No | `''` | — | Persona de contacto. |
| `activo` | `bool` | No | `1` | — | Proveedor habilitado. |
| `creado_en` | `datetime` | No | Automático | — | Fecha de registro. |
| `actualizado_en` | `datetime` | No | Automático | — | Última actualización. |

Restricción `compras_proveedor_nit_unico`: el NIT es único cuando no está
vacío. Varios proveedores pueden no tener NIT.

### 7.2 `compras_compra`

| Columna | Tipo | Nulo | Predeterminado | Clave / restricción | Descripción |
|---|---|---|---|---|---|
| `id` | `bigint` | No | Autoincremental | PK | Identificador. |
| `numero_factura` | `varchar(50)` | No | `''` | — | Número de factura del proveedor. |
| `fecha_compra` | `date` | No | Fecha local | — | Fecha del documento. |
| `fecha_recepcion` | `date` | Sí | `NULL` | — | Fecha en que ingresó la mercadería. |
| `estado` | `varchar(10)` | No | `BORRADOR` | Enum `BORRADOR`, `RECIBIDA`, `ANULADA` | Estado del documento. |
| `subtotal` | `decimal(12,2)` | No | `0.00` | `>= 0` | Suma de líneas, calculada en el servidor. |
| `impuesto` | `decimal(12,2)` | No | `0.00` | `>= 0` | Impuesto calculado en el servidor. |
| `total` | `decimal(12,2)` | No | `0.00` | `>= 0` | `subtotal + impuesto`. |
| `observaciones` | `text` | No | `''` | — | Notas libres. |
| `creado_en` | `datetime` | No | Automático | — | Fecha de registro. |
| `actualizado_en` | `datetime` | No | Automático | — | Última actualización. |
| `usuario_id` | `integer` | No | — | FK → `auth_user.id` (PROTECT) | Usuario que registró la compra. |
| `proveedor_id` | `bigint` | No | — | FK → `compras_proveedor.id` (PROTECT) | Proveedor. |

Índices: `compras_compra_fecha_idx`, `compras_compra_estado_idx`,
`compras_compra_proveedor_id_d647dfa3`, `compras_compra_usuario_id_833384c6`.

Reglas:

- Solo un `BORRADOR` se puede editar o anular.
- `RECIBIDA` y `ANULADA` son inmutables.
- Una compra `RECIBIDA` exige `fecha_recepcion`; otros estados no la admiten.
- Los totales nunca se toman del navegador: los recalcula
  `apps/compras/services.py`.

### 7.3 `compras_detallecompra`

| Columna | Tipo | Nulo | Predeterminado | Clave / restricción | Descripción |
|---|---|---|---|---|---|
| `id` | `bigint` | No | Autoincremental | PK | Identificador. |
| `cantidad` | `integer unsigned` | No | — | `> 0` | Unidades compradas. |
| `costo_unitario` | `decimal(10,2)` | No | — | `>= 0` | Costo por unidad. |
| `subtotal` | `decimal(12,2)` | No | `0.00` | `>= 0` | `cantidad × costo_unitario`. |
| `compra_id` | `bigint` | No | — | FK → `compras_compra.id` (CASCADE) | Compra padre. |
| `lote_id` | `bigint` | Sí | `NULL` | FK → `inventario_lote.id` (PROTECT) | Lote que recibe la línea. |
| `producto_id` | `bigint` | No | — | FK → `catalogo_producto.id` (PROTECT) | Producto comprado. |

Reglas:

- El lote es opcional hasta la recepción.
- En la recepción debe existir un lote activo del mismo producto por línea.
- Un mismo producto puede repetirse en varias líneas, porque cada línea puede
  recibirse en un lote distinto.
- No hay restricción única por (`compra`, `producto`).

## 8. Módulo `inventario`

### 8.1 `inventario_lote`

Unidad de stock. Cada producto puede tener varios lotes.

| Columna | Tipo | Nulo | Predeterminado | Clave / restricción | Descripción |
|---|---|---|---|---|---|
| `id` | `bigint` | No | Autoincremental | PK | Identificador. |
| `codigo_lote` | `varchar(50)` | No | — | UNIQUE por producto | Código normalizado a mayúsculas. |
| `fecha_fabricacion` | `date` | Sí | `NULL` | — | Fecha de fabricación. |
| `fecha_vencimiento` | `date` | Sí | `NULL` | — | Fecha de vencimiento. |
| `fecha_ingreso` | `date` | No | Fecha local | — | Fecha de alta del lote. |
| `stock_actual` | `decimal(12,2)` | No | `0.00` | `>= 0` | Existencias actuales. |
| `activo` | `bool` | No | `1` | — | Lote habilitado. |
| `creado_en` | `datetime` | No | Automático | — | Fecha de registro. |
| `actualizado_en` | `datetime` | No | Automático | — | Última actualización. |
| `producto_id` | `bigint` | No | — | FK → `catalogo_producto.id` (PROTECT) | Producto del lote. |

Restricciones e índices:

- `inventario_lote_unico_por_producto`: único (`producto_id`, `codigo_lote`).
- `inventario_lote_stock_no_negativo`: `stock_actual >= 0`.
- `inventario_lote_prod_venc_idx`: (`producto_id`, `fecha_vencimiento`) para
  consultas FEFO.

Reglas:

- Un lote con `stock_actual > 0` no puede desactivarse.
- La fecha de vencimiento debe ser posterior a la de fabricación.
- El stock solo cambia con movimientos registrados por
  `apps/inventario/services.py`.

### 8.2 `inventario_movimientoinventario`

Movimiento inmutable que explica cada cambio de existencias.

| Columna | Tipo | Nulo | Predeterminado | Clave / restricción | Descripción |
|---|---|---|---|---|---|
| `id` | `bigint` | No | Autoincremental | PK | Identificador. |
| `tipo` | `varchar(20)` | No | — | Enum de tipo de movimiento | Naturaleza del movimiento. |
| `cantidad` | `decimal(12,2)` | No | — | `> 0` | Unidades movidas. |
| `stock_resultante` | `decimal(12,2)` | No | — | `>= 0` | Stock del lote después del movimiento. |
| `costo_total` | `decimal(14,2)` | Sí | `NULL` | — | Costo histórico del movimiento; vacío si no es confiable. |
| `detalle_venta_id` | `bigint` | Sí | `NULL` | FK → `ventas_detalleventa.id` (PROTECT) | Línea de venta que originó la salida. |
| `motivo` | `varchar(200)` | No | `''` | — | Motivo o referencia. |
| `usuario_id` | `integer` | No | — | FK → `auth_user.id` (PROTECT) | Usuario que registró el movimiento. |
| `fecha` | `datetime` | No | Ahora | — | Fecha y hora. |
| `lote_id` | `bigint` | No | — | FK → `inventario_lote.id` (PROTECT) | Lote afectado. |

Índices: `inventario_mov_lote_fecha_idx`, `inventario_mov_fecha_idx`, más los
índices automáticos de las claves foráneas.

Reglas:

- Es inmutable: no tiene edición ni borrado en la interfaz.
- `INICIAL` solo lo crea `crear_lote()`.
- Las salidas y ajustes negativos descuentan; las entradas y ajustes positivos
  suman.
- El formulario manual solo permite `ENTRADA`, `SALIDA`,
  `AJUSTE_POSITIVO` y `AJUSTE_NEGATIVO`.

### 8.3 `inventario_capacosto`

Capa de costo de una entrada: cuántas unidades ingresaron a qué costo unitario
y cuántas quedan disponibles. Permite costeo FIFO dentro de cada lote.

| Columna | Tipo | Nulo | Predeterminado | Clave / restricción | Descripción |
|---|---|---|---|---|---|
| `id` | `bigint` | No | Autoincremental | PK | Identificador. |
| `cantidad_inicial` | `decimal(12,2)` | No | — | `> 0` | Unidades recibidas en la capa. |
| `cantidad_restante` | `decimal(12,2)` | No | — | `0 ≤ restante ≤ inicial` | Unidades aún disponibles. |
| `costo_unitario` | `decimal(10,2)` | Sí | `NULL` | `>= 0` | Costo unitario; `NULL` si es desconocido. |
| `creado_en` | `datetime` | No | Automático | — | Fecha de ingreso. |
| `lote_id` | `bigint` | No | — | FK → `inventario_lote.id` (PROTECT) | Lote de la capa. |
| `movimiento_entrada_id` | `bigint` | Sí | `NULL` | FK → `inventario_movimientoinventario.id` (PROTECT, UNIQUE) | Movimiento que originó la capa. |

Restricciones:

- `inventario_capa_cantidad_inicial_positiva`: `cantidad_inicial > 0`.
- `inventario_capa_cantidad_restante_valida`: rango `0..cantidad_inicial`.
- Un movimiento de entrada puede tener como máximo una capa.

Regla clave: la suma de `cantidad_restante` de las capas de un lote debe
coincidir con `Lote.stock_actual`.

### 8.4 `inventario_asignacioncostoinventario`

Trazabilidad de qué capas consumió cada movimiento de salida.

| Columna | Tipo | Nulo | Predeterminado | Clave / restricción | Descripción |
|---|---|---|---|---|---|
| `id` | `bigint` | No | Autoincremental | PK | Identificador. |
| `cantidad` | `decimal(12,2)` | No | — | `> 0` | Unidades consumidas de la capa. |
| `costo_unitario` | `decimal(10,2)` | Sí | `NULL` | — | Costo aplicado a esas unidades. |
| `movimiento_id` | `bigint` | No | — | FK → `inventario_movimientoinventario.id` (PROTECT) | Movimiento de salida. |
| `capa_id` | `bigint` | No | — | FK → `inventario_capacosto.id` (PROTECT) | Capa consumida. |

Restricciones:

- `inventario_asignacion_cantidad_positiva`: `cantidad > 0`.
- `inventario_asignacion_movimiento_capa_unica`: único
  (`movimiento_id`, `capa_id`).

### 8.5 `inventario_ajustecostoinventario`

Auditoría cuando un administrador completa el costo de existencias heredadas
sin alterar cantidades.

| Columna | Tipo | Nulo | Predeterminado | Clave / restricción | Descripción |
|---|---|---|---|---|---|
| `id` | `bigint` | No | Autoincremental | PK | Identificador. |
| `cantidad` | `decimal(12,2)` | No | — | `> 0` | Unidades valorizadas. |
| `costo_unitario` | `decimal(10,2)` | No | — | `>= 0` | Costo unitario asignado. |
| `motivo` | `varchar(200)` | No | `''` | — | Justificación. |
| `fecha` | `datetime` | No | Automático | — | Fecha del ajuste. |
| `lote_id` | `bigint` | No | — | FK → `inventario_lote.id` (PROTECT) | Lote valorizado. |
| `usuario_id` | `integer` | No | — | FK → `auth_user.id` (PROTECT) | Administrador que registró el ajuste. |

## 9. Módulo `ventas`

### 9.1 `ventas_venta`

Cabecera de una venta confirmada. Es inmutable desde la interfaz.

| Columna | Tipo | Nulo | Predeterminado | Clave / restricción | Descripción |
|---|---|---|---|---|---|
| `id` | `bigint` | No | Autoincremental | PK | Identificador. |
| `metodo_pago` | `varchar(20)` | No | `EFECTIVO` | Enum `EFECTIVO` | Medio de pago. |
| `monto_recibido` | `decimal(12,2)` | No | — | `>= 0` y `>= total` | Efectivo entregado por el cliente. |
| `total` | `decimal(12,2)` | No | `0.00` | `>= 0` | Total calculado en el servidor. |
| `creado_en` | `datetime` | No | Automático | — | Fecha y hora de la venta. |
| `cliente_id` | `bigint` | Sí | `NULL` | FK → `clientes_cliente.id` (PROTECT) | Cliente; vacío = consumidor final. |
| `vendedor_id` | `integer` | No | — | FK → `auth_user.id` (PROTECT) | Usuario que registró la venta. |

Restricciones:

- `ventas_total_no_negativo`.
- `ventas_monto_recibido_no_negativo`.
- `ventas_monto_recibido_cubre_total`: `monto_recibido >= total`.

### 9.2 `ventas_detalleventa`

Línea de venta con copia histórica del producto y de su costo.

| Columna | Tipo | Nulo | Predeterminado | Clave / restricción | Descripción |
|---|---|---|---|---|---|
| `id` | `bigint` | No | Autoincremental | PK | Identificador. |
| `codigo_producto` | `varchar(30)` | No | — | — | Código del producto al momento de la venta. |
| `nombre_producto` | `varchar(150)` | No | — | — | Nombre del producto al momento de la venta. |
| `cantidad` | `integer unsigned` | No | — | `> 0` | Unidades vendidas. |
| `precio_unitario` | `decimal(10,2)` | No | — | `>= 0` | Precio aplicado. |
| `costo_total` | `decimal(14,2)` | Sí | `NULL` | — | Costo histórico de las unidades; vacío si no es confiable. |
| `creado_en` | `datetime` | No | Automático | — | Fecha de registro. |
| `producto_id` | `bigint` | No | — | FK → `catalogo_producto.id` (PROTECT) | Producto vendido. |
| `venta_id` | `bigint` | No | — | FK → `ventas_venta.id` (CASCADE) | Venta padre. |

Restricciones:

- `ventas_detalle_cantidad_positiva`.
- `ventas_detalle_precio_no_negativo`.
- `ventas_detalle_producto_unico_por_venta`: un producto no puede repetirse en
  la misma venta.

Regla: el subtotal de la línea es `cantidad × precio_unitario` y no se almacena;
se calcula en el modelo. La ganancia bruta es
`subtotal − costo_total` cuando el costo es conocido.

## 10. Tablas de infraestructura Django

Estas tablas las crea Django y no forman parte del dominio de la farmacia. Se
incluyen en el script SQL para que el esquema sea completo.

| Tabla | Propósito | Columnas principales |
|---|---|---|
| `auth_user` | Usuarios del sistema. | `id`, `username` (único), `password`, `first_name`, `last_name`, `email`, `is_active`, `is_staff`, `is_superuser`, `last_login`, `date_joined`. |
| `auth_group` | Roles `Administrador` y `Vendedor`. | `id`, `name` (único). |
| `auth_permission` | Permisos por modelo. | `id`, `content_type_id`, `codename`, `name`. |
| `auth_user_groups` | Relación N:M usuario–grupo. | `user_id`, `group_id`; único por par. |
| `auth_group_permissions` | Permisos asignados a grupos. | `group_id`, `permission_id`; único por par. |
| `auth_user_user_permissions` | Permisos directos por usuario. | `user_id`, `permission_id`; único por par. |
| `django_content_type` | Tipos de contenido (app + modelo). | `app_label`, `model`; único por par. |
| `django_admin_log` | Auditoría del Django Admin. | `user_id`, `content_type_id`, `object_id`, `action_flag`, `change_message`, `action_time`. |
| `django_migrations` | Migraciones aplicadas. | `app`, `name`, `applied`. |
| `django_session` | Sesiones activas. | `session_key` (PK), `session_data`, `expire_date`. |

Los permisos y sus asignaciones se generan en `post_migrate` y con
`python manage.py sync_roles`. El script SQL solo crea los grupos base y la
categoría `General`.

## 11. Enumeraciones del dominio

### 11.1 Tipo de documento — `clientes_cliente.tipo_documento`

| Valor | Etiqueta |
|---|---|
| `CI` | Cédula de Identidad |
| `NIT` | NIT |
| `PASAPORTE` | Pasaporte |
| `OTRO` | Otro |

Vacío permitido (`''`) cuando no se registra documento. Si hay tipo, debe haber
número; si hay número, debe haber tipo.

### 11.2 Estado de compra — `compras_compra.estado`

| Valor | Etiqueta | Efecto |
|---|---|---|
| `BORRADOR` | Borrador | Editable y anulable; no afecta stock. |
| `RECIBIDA` | Recibida | Inmutable; registró entradas de inventario. |
| `ANULADA` | Anulada | Inmutable; no afecta stock. |

### 11.3 Tipo de movimiento — `inventario_movimientoinventario.tipo`

| Valor | Etiqueta | Signo sobre el stock |
|---|---|---|
| `INICIAL` | Inventario inicial | Suma |
| `ENTRADA` | Entrada | Suma |
| `SALIDA` | Salida | Resta |
| `AJUSTE_POSITIVO` | Ajuste positivo | Suma |
| `AJUSTE_NEGATIVO` | Ajuste negativo | Resta |

### 11.4 Método de pago — `ventas_venta.metodo_pago`

| Valor | Etiqueta |
|---|---|
| `EFECTIVO` | Efectivo |

## 12. Reglas de negocio transversales

1. **Inventario es la única fuente de stock.** Ningún módulo escribe
   `Lote.stock_actual` directamente. Todo cambio pasa por
   `apps/inventario/services.py`.
2. **Movimientos inmutables.** `MovimientoInventario` no se edita ni se elimina.
   Su admin es de solo lectura.
3. **Ventas inmutables.** No hay edición, borrado ni anulación desde la
   interfaz. `VentaAdmin` es de solo lectura.
4. **Compras controladas por estado.** Solo los borradores se editan o anulan;
   las recibidas y anuladas no se modifican ni se eliminan.
5. **Recepción atómica.** Se validan todas las líneas antes de registrar
   cualquier movimiento; si una falla, no se aplica ninguna.
6. **Recepción sobre lotes existentes.** No se crean lotes durante la
   recepción. Cada línea usa un lote activo del mismo producto y ningún lote se
   reutiliza entre líneas.
7. **Costeo FIFO por lote.** Las salidas consumen primero las capas de costo más
   antiguas. La suma de capas restantes debe igualar el stock del lote.
8. **Costos desconocidos no se inventan.** Las existencias heredadas sin costo
   quedan con `costo_unitario = NULL` hasta un ajuste auditado.
9. **Documentos opcionales pero coherentes.** En clientes, tipo y número van
   juntos; el número es único por tipo cuando existe.
10. **NIT de proveedor único.** Se normaliza a mayúsculas y no se repite cuando
    está presente.
11. **Códigos de producto y lote normalizados.** Se guardan en mayúsculas; el
    código de producto es único y el de lote es único por producto.
12. **Desactivación con existencias.** Un lote con stock no se desactiva; una
    categoría con productos activos tampoco.
13. **Configuración única.** `ConfiguracionSistema` mantiene una sola fila
    lógica (`pk = 1`).
14. **Cálculos en el servidor.** Totales de compra y venta se calculan en los
    servicios; el navegador solo muestra una vista previa.

## 13. Relaciones principales

```text
auth_user 1 ─── N compras_compra
auth_user 1 ─── N ventas_venta
auth_user 1 ─── N inventario_movimientoinventario
auth_user 1 ─── N inventario_ajustecostoinventario
auth_user 1 ─── N clientes_cliente

catalogo_categoria 1 ─── N catalogo_producto
catalogo_laboratorio 1 ─── N catalogo_producto
catalogo_formafarmaceutica 1 ─── N catalogo_producto
catalogo_presentacion 1 ─── N catalogo_producto

catalogo_producto 1 ─── N inventario_lote
inventario_lote 1 ─── N inventario_movimientoinventario
inventario_lote 1 ─── N inventario_capacosto
inventario_lote 1 ─── N inventario_ajustecostoinventario

inventario_movimientoinventario 1 ─── N inventario_asignacioncostoinventario
inventario_capacosto 1 ─── N inventario_asignacioncostoinventario
inventario_movimientoinventario 1 ─── 0..1 inventario_capacosto

compras_proveedor 1 ─── N compras_compra
compras_compra 1 ─── N compras_detallecompra
catalogo_producto 1 ─── N compras_detallecompra
inventario_lote 1 ─── N compras_detallecompra

clientes_cliente 1 ─── N ventas_venta
ventas_venta 1 ─── N ventas_detalleventa
catalogo_producto 1 ─── N ventas_detalleventa
ventas_detalleventa 1 ─── N inventario_movimientoinventario
```

## 14. Inventario de restricciones

| Tabla | Restricción | Tipo |
|---|---|---|
| `catalogo_producto` | `catalogo_producto_precio_no_negativo` | CHECK |
| `catalogo_producto` | `catalogo_producto_stock_minimo_no_negativo` | CHECK |
| `clientes_cliente` | `clientes_documento_tipo_numero_coherentes` | CHECK |
| `clientes_cliente` | `clientes_documento_unico_por_tipo` | UNIQUE parcial |
| `compras_proveedor` | `compras_proveedor_nit_unico` | UNIQUE parcial |
| `compras_compra` | `compras_compra_subtotal_no_negativo` | CHECK |
| `compras_compra` | `compras_compra_impuesto_no_negativo` | CHECK |
| `compras_compra` | `compras_compra_total_no_negativo` | CHECK |
| `compras_detallecompra` | `compras_detalle_cantidad_positiva` | CHECK |
| `compras_detallecompra` | `compras_detalle_costo_no_negativo` | CHECK |
| `compras_detallecompra` | `compras_detalle_subtotal_no_negativo` | CHECK |
| `inventario_lote` | `inventario_lote_unico_por_producto` | UNIQUE |
| `inventario_lote` | `inventario_lote_stock_no_negativo` | CHECK |
| `inventario_movimientoinventario` | `inventario_mov_cantidad_positiva` | CHECK |
| `inventario_movimientoinventario` | `inventario_mov_stock_no_negativo` | CHECK |
| `inventario_capacosto` | `inventario_capa_cantidad_inicial_positiva` | CHECK |
| `inventario_capacosto` | `inventario_capa_cantidad_restante_valida` | CHECK |
| `inventario_asignacioncostoinventario` | `inventario_asignacion_cantidad_positiva` | CHECK |
| `inventario_asignacioncostoinventario` | `inventario_asignacion_movimiento_capa_unica` | UNIQUE |
| `ventas_venta` | `ventas_total_no_negativo` | CHECK |
| `ventas_venta` | `ventas_monto_recibido_no_negativo` | CHECK |
| `ventas_venta` | `ventas_monto_recibido_cubre_total` | CHECK |
| `ventas_detalleventa` | `ventas_detalle_cantidad_positiva` | CHECK |
| `ventas_detalleventa` | `ventas_detalle_precio_no_negativo` | CHECK |
| `ventas_detalleventa` | `ventas_detalle_producto_unico_por_venta` | UNIQUE |

## 15. Mantenimiento del documento

Cuando se agregue o modifique un modelo:

1. Crear la migración en la app correspondiente.
2. Ejecutar `python manage.py migrate`.
3. Actualizar [`script-creacion-bd.sql`](script-creacion-bd.sql) con el DDL e
   índices nuevos.
4. Actualizar este diccionario con las columnas, restricciones y reglas.
5. Registrar el cambio en [`../CHANGELOG.md`](../CHANGELOG.md).
6. Verificar con `python manage.py check`,
   `python manage.py makemigrations --check --dry-run` y
   `python manage.py test`.
