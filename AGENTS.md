# AGENTS.md

## Project shape

- Django 6.1.1 monolith (Python >=3.12, SQLite), server-rendered MVT. No SPA,
  REST API, React, CDN, or external fonts.
- `config/` holds settings and the root URLconf. The eight apps live under
  `apps/`: `core`, `accounts`, `catalogo`, `inventario`, `compras`, `clientes`,
  `ventas`, `reportes`. App config `name` values are `apps.<app>`; app labels
  are the short names.
- Templates are project-level in `templates/<app>/` (not app-local); shared
  pieces are in `templates/includes/`. Static assets are local in `static/`.
- `README.md` covers setup and routes; `docs/ARCHITECTURE.md` covers module
  boundaries; decisions are in `docs/adr/`; changes belong in `CHANGELOG.md`.

## Commands

Run from the repo root with the virtualenv active (there is no checked-in
`.venv`):

```bash
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Verification, all expected to pass before a PR:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

Focused tests:

```bash
# One app
python manage.py test apps.ventas

# One test case / method
python manage.py test apps.ventas.tests.VentaServiceTests
python manage.py test apps.ventas.tests.VentaServiceTests.test_registra_venta_con_detalles_y_calcula_total
```

- Tests use Django's runner, not pytest. There is no pytest, ruff, black, or
  mypy configuration, so do not invent lint/format commands.
- Tests use a temporary database and do not modify `db.sqlite3`.
- Transversal tests are in `tests/test_smoke.py`; each implemented app also has
  `apps/<app>/tests.py`.
- `tests/test_smoke.py` asserts route names and role access. When adding routes,
  update `test_initial_routes_resolve`,
  `test_management_views_require_authentication`, the seller `403` checks, and
  the administrator access list.

## Domain and architecture rules

- Keep the eight-app layout. `Proveedor` belongs in `compras`; do not create a
  ninth app for it.
- `core` is shared infrastructure only. `reportes` is read-only and owns no
  models.
- `inventario` is the sole owner of stock. All stock changes go through
  `apps/inventario/services.py`: `crear_lote()` registers the initial movement
  and `registrar_movimiento()` updates `Lote.stock_actual` and creates an
  immutable `MovimientoInventario` inside `transaction.atomic()`. Sales and
  purchases must use these services; never decrement stock directly from
  `ventas` or `compras`.
- `Lote` is the unit of stock. A lot with `stock_actual > 0` cannot be
  deactivated. Lot codes are normalized to uppercase and unique per product,
  case-insensitively. The manual movement form offers only `ENTRADA`, `SALIDA`,
  `AJUSTE_POSITIVO`, and `AJUSTE_NEGATIVO`; `INICIAL` is created only by
  `crear_lote()`.
- `MovimientoInventario` is immutable: no edit or delete UI, and its admin is
  read-only. `LoteAdmin` treats `stock_actual` as read-only and does not allow
  deletion. Low-stock alerts use `stock_total <= stock_minimo` for active
  products via `apps/inventario/selectors.py`.
- The only write path for sales is `apps/ventas/services.py:registrar_venta`.
  It runs inside `transaction.atomic()`, takes prices from `Producto`, and
  stores a historical copy in `DetalleVenta`. The browser preview is not
  authoritative.
- Sales are immutable: no edit, delete, or cancel UI, and `VentaAdmin` is
  read-only. Do not add those operations without an explicit product decision.
- The only write paths for purchases are `apps/compras/services.py`:
  `registrar_compra()`, `actualizar_compra()`, `recibir_compra()`, and
  `anular_compra()`. They run inside `transaction.atomic()` and calculate
  `subtotal = Σ(cantidad × costo_unitario)` and `total = subtotal + impuesto` on
  the server. Never trust totals posted by the browser.
- Purchase states are `BORRADOR`, `RECIBIDA`, and `ANULADA`. Only drafts can be
  edited or cancelled. Received and cancelled purchases are immutable and are
  not deleted; `CompraAdmin` is read-only for them, and providers/purchases
  never get delete permission.
- Reception requires one existing active lot per line, belonging to the line's
  product, and no lot may be reused across lines. It registers `ENTRADA`
  movements through `apps/inventario/services.py`; it never creates lots or
  edits `Lote.stock_actual` directly. `DetalleCompra.lote` stays optional until
  reception. Reception is atomic: validate every line before any movement.
- Repeating a product across purchase lines is allowed because each line may
  receive a different lot. `Proveedor.nit` is optional but unique
  case-insensitively when present. The whole `compras` module is
  administrator-only; sellers receive `403`.
- The project uses Django's built-in `User`. Roles are the groups
  `Administrador` and `Vendedor`, defined in `apps/accounts/constants.py` and
  created by the data migration `accounts.0001_create_default_groups`.
  Use `RoleRequiredMixin` from `apps/core/mixins.py` for group-restricted views;
  superusers bypass it.
- `Cliente` intentionally has no email or address fields. Document type and
  number are optional but must be provided together, with the number unique
  per type.
- Catalog product and category CRUD is visual and lives in `catalogo`. Sellers
  get read-only access; only administrators create, edit, or deactivate.
  `Laboratorio`, `FormaFarmaceutica`, and `Presentacion` remain admin-managed.
  Categories with active products cannot be deactivated, and catalog records
  are never deleted (use `activo`). Products own no stock: stock lives in
  `inventario`.
- Never edit an applied migration; create a new one. Run `makemigrations` in the
  app that owns the changed model.

## Conventions

- Domain names, user-facing text, and docs are in Spanish; Django concepts stay
  in English. Avoid accents in code identifiers (`Categoria`, not `Categoría`).
- Give every app a URL namespace and keep existing route names stable; smoke
  tests assert them.
- Validate on the server. All writes use POST plus CSRF; logout is POST-only.
- Do not reintroduce CDN assets or external fonts; smoke tests assert their
  absence. Keep sale-form JS hooks (`data-precio`, `data-line-*`,
  `data-sale-received`) in sync with `static/js/ventas.js`, and purchase-form
  hooks (`data-compra-*`) in sync with `static/js/compras.js`.
- Business validation is intentionally repeated at the model, form, and service
  layers for sales, clients, and catalog. When changing a rule, update all
  relevant layers and their tests.

## Environment and git gotchas

- Settings read environment variables directly; there is no automatic `.env`
  loading. Relevant variables: `DJANGO_DEBUG`, `DJANGO_SECRET_KEY`,
  `DJANGO_ALLOWED_HOSTS`, `DJANGO_TIME_ZONE` (default `America/La_Paz`).
- With `DJANGO_DEBUG=False`, a non-default `DJANGO_SECRET_KEY` is mandatory or
  Django refuses to start.
- `db.sqlite3`, `.env*`, `staticfiles/`, and `media/` are git-ignored. Never
  commit them.
- Branch reality differs from the README: the repo has `main`, `erlan`, and
  `jose` (locally and on `origin`), with no `develop` branch. Run
  `git branch -a` and confirm the target branch before creating a branch or PR.
- Docs can lag the code (for example, `reportes` now has real views/templates
  while README status text still calls it a placeholder). Trust the code and
  tests over status tables, and update the docs when behavior changes.
