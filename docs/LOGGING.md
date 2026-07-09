# Sistema de Logs

## Configuración

Logging estándar de Python configurado en `scheduler/auto_scheduler.py`:

```python
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
```

## Convenciones

- Cada módulo usa `logger = logging.getLogger(__name__)` para identificar el origen
- Separadores `=` × 60 al inicio de cada job para delimitar ciclos
- Emojis como indicadores visuales rápidos:
  - `✓` éxito, `✗` fallo
  - `🖼` operaciones de imagen
  - `📘` Facebook, `📱` Telegram, `📧` newsletter, `📄` PDF
  - `🔥` breaking story o cluster multi-medio
  - `🧹` auto-limpieza

## Niveles

| Nivel | Uso |
|-------|-----|
| `INFO` | Operaciones normales, conteos, progreso |
| `WARNING` | Situaciones recuperables (feed con errores, imagen no encontrada, fallback activado) |
| `ERROR` | Fallos en operaciones (API errors, BD errors) con `exc_info=True` para stack trace |
| `DEBUG` | Duplicados detectados, artículos filtrados, detalles internos |

## Almacenamiento

Los logs se emiten a stdout/stderr. En Railway, se visualizan en tiempo real vía el Dashboard. No se persisten en archivos (`.gitignore` excluye `*.log` y `logs/`).

## Diagnóstico

El script `neurodiario/tools/Db_stats` genera un reporte visual de la BD con barras de texto, sin modificar datos.
