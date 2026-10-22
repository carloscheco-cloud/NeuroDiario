# Publicación de NeuroDiario por WAHA

El mismo `social_sync` que distribuye a Telegram ahora puede publicar en el canal
de WhatsApp. Reutiliza `GeneratedArticle.title`, la URL real de WordPress y la
imagen seleccionada en ese ciclo. No lee Telegram, no usa RSS ni vuelve a generar
el artículo con IA. Procesa un artículo por ciclo, cada 12 minutos.

La integración está desactivada por defecto. La configuración antigua de
Make.com/Whapi.Cloud no está operativa y no se utiliza.

## Requisitos y red

- Añadir el número de la sesión WAHA como administrador del canal de NeuroDiario
  y aceptar la invitación en el teléfono. Seguir el canal no concede permisos.
- Mantener esa sesión en `WORKING`; WEBJS admite texto e imágenes en canales.
- Ejecutar el chequeo desde el contenedor/servidor que ejecuta NeuroDiario.
- En el mismo VPS: conectar ambos contenedores a una red Docker privada compartida.
  `http://universidad-waha-1:3000` es válido solo si ese nombre resuelve desde NeuroDiario.
- En otro servidor, como Railway: usar una conexión privada/VPN o un túnel de
  servicio con TLS y autenticación hasta WAHA. `localhost:3010` apunta al propio
  servidor de NeuroDiario y no al VPS. El túnel SSH abierto en tu PC no conecta Railway.
  No cambiar el puerto loopback de WAHA por un puerto público para resolver esto.

## Variables

```dotenv
WHATSAPP_ENABLED=false
WAHA_URL=http://universidad-waha-1:3000
WAHA_API_KEY=clave_original_privada_de_waha
WAHA_SESSION=default
WHATSAPP_CHANNEL_ID=120363412361118712@newsletter
WHATSAPP_START_AT=2026-10-22T00:00:00Z
```

El ID es el que documenta el repositorio: comprobar que sigue siendo el canal
correcto. La clave es la original de WAHA, nunca su hash. No subirla a GitHub ni
incluirla en capturas. La fecha es un ejemplo: escoger el inicio real de la
distribución para no volcar todo el histórico. Se compara con `published_at` UTC.
Los artículos anteriores o sin fecha de publicación se omiten para WhatsApp.

## Activación

1. Desplegar el código de esta integración en NeuroDiario.
2. Configurar las variables conservando `WHATSAPP_ENABLED=false`.
3. Preparar la tabla nueva, sin alterar las tablas existentes:

   ```bash
   python migrate_whatsapp_publications.py
   ```

4. Comprobar red, sesión y rol del canal sin enviar mensajes:

   ```bash
   python -m neurodiario.tools.check_waha
   ```

5. Cambiar `WHATSAPP_ENABLED=true` y reiniciar el scheduler. Revisar la primera
   noticia que se publique después de la fecha inicial. Los siguientes ciclos
   no repiten una entrega confirmada del mismo artículo/canal.

Al habilitarse, el scheduler también intenta crear la tabla con `checkfirst=True`.
Si no tiene permisos para prepararla, WhatsApp queda desactivado en ese ciclo y
Telegram/Facebook conservan su flujo.

## Resultado y recuperación

La tabla `whatsapp_publications` tiene una restricción única por artículo y canal.
Se confirma una reserva `sending` antes de llamar a WAHA. Un worker concurrente
no puede reservar otra entrega del mismo artículo/canal.

| Estado | Significado |
|---|---|
| `sent` | WAHA devolvió un ID de mensaje; se conserva también la fecha. |
| `failed` | Rechazo confirmado. Solo límites temporales y timeout de conexión se reintentan, con espera y máximo tres intentos. |
| `uncertain` | Timeout de lectura, desconexión, error 5xx o respuesta sin ID. Revisar el canal antes de cualquier reenvío. |
| `sending` | Reserva pendiente; si el proceso se interrumpió, reconciliar manualmente. |

El fallback de imagen a texto se usa solo ante rechazo HTTP 400/422 de la imagen.
No hay fallback ni reenvío automático tras una respuesta ambigua. Esto reduce
duplicados, pero no promete entrega exactamente una vez ante fallos de red.

Los errores permanentes y entregas inciertas no bloquean otras noticias ni
provocan que se repita su publicación en Telegram. Su reconciliación es manual
en esta primera versión. Para pausar, poner `WHATSAPP_ENABLED=false` y reiniciar.

## Pruebas

```bash
python -m pytest tests/test_whatsapp.py -q
```

Las pruebas usan SQLite y transporte WAHA simulado. Verifican datos compartidos
con Telegram, permisos, migración, duplicados, dos workers, reinicios de sesión
de BD, límites y fallos de red. La entrega real se verifica durante la activación.
