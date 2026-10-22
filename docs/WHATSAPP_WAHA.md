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

## Instalación localizada en el VPS de Carlos

`scripts/install_waha_vps.py` está preparado para `/opt/apps/NeuroDiario`,
servicio `neurodiario` y contenedor `neurodiario_app` sobre el commit VPS
`313a193e4c783cd16656b2311d42b1cce3c4945c`. No cambia de rama ni sobrescribe
los cambios locales de generación y requisitos. El payload añade WAHA al
scheduler de esa versión y conserva su cola de borradores, prioridad de imágenes,
configuración OpenAI y modelo MediaAsset.

Antes de modificar nada comprueba hashes de los archivos afectados tanto en el
host como dentro del contenedor activo, y verifica sesión y permiso del canal.
La clave se reutiliza del contenedor del asistente universitario sin imprimirla;
si falta, se solicita por entrada oculta.

```bash
python3 scripts/install_waha_vps.py --check-only
python3 scripts/install_waha_vps.py
```

Se puede indicar otro ID mediante `--channel ID@newsletter`. La comprobación
no envía mensajes. La instalación guarda respaldo e imagen anterior, añade la
red `universidad_default` al Compose existente y mantiene la clave en un archivo
0600 fuera del contexto de construcción: `/opt/apps/.NeuroDiario-waha.env`.
Construye la imagen mientras el contenedor anterior sigue funcionando, prepara
solo la tabla nueva y reinicia únicamente NeuroDiario. Ante fallo restaura las
fuentes y etiqueta de imagen anteriores; si el reinicio había comenzado, vuelve
a levantar la versión previa. La tabla adicional se conserva sin alterar las
existentes.

El inicio de distribución es el momento de la instalación, en UTC. No publica
el histórico ni envía una noticia de prueba; hay que comprobar la primera entrega
real del ciclo. Para pausar, cambiar `WHATSAPP_ENABLED=false` en el archivo de
configuración anterior y recrear solo el servicio con Docker Compose.

La variante VPS pasó las 24 pruebas de publicación; el instalador tiene otras
7 pruebas de precondiciones, permisos, recuperación y configuración privada.
Los chequeos reales de red, sesión y canal se ejecutan en el VPS.
