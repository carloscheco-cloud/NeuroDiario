# Contribuir

## Cómo Contribuir

1. **Fork** del repositorio en GitHub
2. **Clonar** tu fork: `git clone https://github.com/TU-USUARIO/NeuroDiario.git`
3. **Crear rama**: `git checkout -b feature/descripcion-corta`
4. **Hacer cambios** siguiendo las convenciones del proyecto
5. **Ejecutar tests**: `pytest neurodiario/tests/ -v`
6. **Commit** con mensajes descriptivos en español
7. **Push**: `git push origin feature/descripcion-corta`
8. **Pull Request** con descripción detallada

## Convenciones

- **Idioma**: código y comentarios en español, nombres de variables en inglés cuando sea estándar (ej: `url`, `response`, `config`)
- **Docstrings**: en español, formato descriptivo con Args/Returns
- **Tests**: un test class por módulo, métodos descriptivos
- **Commits**: mensajes claros en español describiendo el cambio

## Estructura de un PR

- Título descriptivo del cambio
- Descripción del problema que resuelve
- Cómo se probó
- Impacto en otros módulos (si aplica)

## Reportar Bugs

Abrir un Issue en GitHub con:
- Descripción del problema
- Pasos para reproducir
- Comportamiento esperado vs actual
- Logs relevantes (sin credenciales)
