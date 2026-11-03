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
- `tests/test_smoke.py` hardcodes which modules render
  `core/placeholder.html` (`catalogo`, `inventario`, `compras`, `reportes`).
  When replacing a placeholder with a real page, update
  `test_seller_can_access_dashboard_and_modules`; otherwise the suite fails for
  the wrong reason.

## Domain and architecture rules

- Keep the eight-app layout. `Proveedor` belongs in `compras`; do not create a
  ninth app for it.
- `core` is shared infrastructure only. `reportes` is read-only and owns no
  models.
- `inventario` is the sole owner of stock. Sales and purchases must eventually
  request stock movements through transactional services; do not decrement
  stock directly from `ventas` or `compras` now.
- The only write path for sales is `apps/ventas/services.py:registrar_venta`.
  It runs inside `transaction.atomic()`, takes prices from `Producto`, and
  stores a historical copy in `DetalleVenta`. The browser preview is not
  authoritative.
- Sales are immutable: no edit, delete, or cancel UI, and `VentaAdmin` is
  read-only. Do not add those operations without an explicit product decision.
- The project uses Django's built-in `User`. Roles are the groups
  `Administrador` and `Vendedor`, defined in `apps/accounts/constants.py` and
  created by the data migration `accounts.0001_create_default_groups`.
  Use `RoleRequiredMixin` from `apps/core/mixins.py` for group-restricted views;
  superusers bypass it.
- `Cliente` intentionally has no email or address fields. Document type and
  number are optional but must be provided together, with the number unique
  per type.
- The catalog is currently just `Producto` (code, name, sale price, active),
  managed from Django Admin. Visual catalog CRUD does not exist yet.
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
  `data-sale-received`) in sync with `static/js/ventas.js`.
- Business validation is intentionally repeated at the model, form, and service
  layers for sales and clients. When changing a rule, update all relevant
  layers and their tests.

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
