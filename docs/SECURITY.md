# Seguridad

## Variables Sensibles

Todas las credenciales se cargan desde variables de entorno via `python-dotenv`. Nunca están hardcodeadas en el código fuente.

### Archivos que NUNCA deben subirse a Git

- `.env` (incluido en `.gitignore`)
- Cualquier archivo con tokens, contraseñas o API keys
- Archivos `.db` o `.sqlite` con datos de producción

## Autenticación

### WordPress
- Application Passwords con HTTPBasicAuth sobre HTTPS
- XML-RPC está bloqueado en el servidor (GreenGeeks)
- Las credenciales viajan cifradas vía TLS

### Facebook
- Page Access Token permanente obtenido vía `GET /me/accounts`
- Los tokens de usuario de corta vida expiran y rompen la automatización

### Telegram
- Bot Token creado vía @BotFather
- Canal público con el bot como administrador

### Claude AI
- API Key de Anthropic almacenada como variable de entorno

### Mailchimp
- API Key con formato `key-serverPrefix`
- Audience ID específico

## Protección de Imágenes

Los medios dominicanos comerciales están bloqueados como fuentes de imágenes (17 dominios) para evitar:
- Uso de fotos con marca de agua
- Infracción de derechos de autor
- CDNs de redes sociales que no cargan en WordPress

## Docker

El Dockerfile elimina del contenedor de producción:
- Directorio `.git`
- Documentación (`docs/`, `*.md`)
- Tests

## Scripts Destructivos

Los scripts `limpiar_base_datos.py` y `limpiar_wordpress.py` tienen triple confirmación:
1. Dry-run por defecto
2. Requieren `--apply`
3. Piden escribir `BORRAR` para confirmar
