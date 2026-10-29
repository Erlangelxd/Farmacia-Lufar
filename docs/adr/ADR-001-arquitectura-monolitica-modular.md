# ADR-001: Monolito modular con Django MVT

**Estado:** Aceptado

## Contexto

El sistema será usado inicialmente de forma local en Farmacia Lufar, por un equipo de dos desarrolladores y sin dependencia de servicios en la nube. El alcance incluye productos, inventario, compras, clientes, ventas, usuarios y reportes. No se requiere una SPA ni una API independiente en esta etapa.

## Decisión

Construir un único proyecto Django con ocho aplicaciones organizadas por dominio, renderizado mediante plantillas de Django y recursos estáticos locales. La configuración del proyecto vive en `config/` y las apps en `apps/`.

## Consecuencias

### Positivas

- Menos infraestructura y menor complejidad operativa.
- Autenticación, formularios, admin, CSRF y ORM vienen integrados.
- Un solo despliegue y una sola base de datos.
- Las apps permiten separar responsabilidades sin microservicios.
- El equipo puede trabajar por módulos con ramas independientes.

### Negativas

- La interfaz no será tan interactiva como una SPA sin agregar JavaScript.
- El monolito requiere disciplina para evitar acoplamiento entre apps.
- Un despliegue único implica que todos los módulos se liberan juntos.

### Riesgos

- Crecimiento desordenado de vistas o modelos. Mitigación: límites de módulo, servicios para reglas complejas y revisión de PR.
- Dependencias circulares entre inventario, compras y ventas. Mitigación: referencias por cadena y servicios transaccionales.

## Alternativas descartadas

- **SPA + API REST:** más piezas, autenticación por tokens y despliegue adicional sin beneficio claro para el alcance inicial.
- **Microservicios:** sobreingeniería para un sistema local y un equipo de dos personas.
- **Una sola app Django:** dificultaría la separación de responsabilidades y el trabajo paralelo.
