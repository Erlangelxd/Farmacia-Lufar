# ADR-003: SQLite y operación local sin CDN

**Estado:** Aceptado

## Contexto

El sistema debe funcionar inicialmente de forma local, sin servicios en la nube ni una conexión permanente a Internet. El equipo necesita una puesta en marcha sencilla y recursos de interfaz disponibles sin red.

## Decisión

Usar SQLite como base de datos inicial y servir todos los recursos de interfaz (CSS, JavaScript e imágenes) desde `static/`. No se usarán CDN, fuentes externas ni APIs de terceros.

## Consecuencias

### Positivas

- SQLite viene incluido con Python y no requiere instalar un servidor de base de datos.
- El respaldo inicial es un único archivo (`db.sqlite3`).
- La interfaz funciona sin conexión después de instalar las dependencias.
- Menos variables de entorno y menor costo de mantenimiento.

### Negativas

- SQLite tiene limitaciones de escritura concurrente y no es la opción ideal para muchos usuarios simultáneos.
- Los recursos locales deben mantenerse en el repositorio.
- Las dependencias de Python todavía requieren instalación inicial.

### Riesgos

- Pérdida del archivo de base de datos. Mitigación: respaldos periódicos y exclusión de `db.sqlite3` del repositorio.
- Crecimiento del sistema a múltiples sucursales o alta concurrencia. Mitigación: evaluar PostgreSQL antes de producción.

## Alternativas descartadas

- **PostgreSQL desde el inicio:** mayor robustez, pero infraestructura innecesaria para la etapa local.
- **CDN para estilos y scripts:** rompe el requisito de funcionamiento local y agrega dependencia externa.
- **Base de datos en la nube:** contradice el alcance inicial.
