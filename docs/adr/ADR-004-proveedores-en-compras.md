# ADR-004: Proveedores dentro de compras

**Estado:** Aceptado

## Contexto

El contexto del proyecto menciona la gestión de proveedores, pero la estructura obligatoria define ocho aplicaciones y no incluye una app `proveedores`. Crear una novena app sin una necesidad funcional concreta agregaría fragmentación.

## Decisión

Ubicar el modelo `Proveedor` en la app `compras`, junto con `Compra` y `DetalleCompra`. La app `compras` será responsable del ciclo de abastecimiento y de la relación con proveedores.

## Consecuencias

### Positivas

- Se respeta la estructura de ocho aplicaciones.
- Proveedor y compra comparten el mismo contexto de negocio.
- Menos navegación y menos apps para el alcance inicial.

### Negativas

- La app `compras` concentra dos responsabilidades relacionadas.
- Si proveedores crece (contactos, evaluaciones, cuentas por pagar), podría necesitar una app propia.

### Riesgos

- Acoplamiento excesivo dentro de `compras`. Mitigación: separar modelos, formularios y servicios cuando la complejidad lo justifique.

## Alternativas descartadas

- **Crear `apps/proveedores`:** válido a futuro, pero fuera de la estructura acordada para esta etapa.
- **Ubicar proveedores en `core`:** `core` no debe contener modelos de negocio.
