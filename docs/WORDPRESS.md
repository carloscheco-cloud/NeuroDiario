# Integración con WordPress

## Método de Conexión

NeuroDiario se comunica con WordPress exclusivamente a través de la **REST API** (`/wp-json/wp/v2/`). XML-RPC está bloqueado en el servidor (GreenGeeks).

## Autenticación

Utiliza HTTPBasicAuth con Application Passwords de WordPress:

```
Authorization: Basic base64(usuario:application_password)
```

La conexión requiere HTTPS. Intentar con HTTP causa errores 401.

## Operaciones

### Publicación de Artículos

**Endpoint**: `POST /wp-json/wp/v2/posts`

```json
{
    "title": "Título del artículo",
    "content": "<p>Contenido HTML...</p>",
    "status": "publish",
    "categories": [12, 34],
    "tags": [56, 78],
    "featured_media": 42
}
```

### Subida de Imágenes

**Endpoint**: `POST /wp-json/wp/v2/media`

1. Descarga la imagen desde la URL con headers de browser
2. Detecta el Content-Type (image/jpeg, image/png, image/webp)
3. Sube el binario con Content-Disposition y Content-Type
4. El Media ID resultante se asigna como `featured_media` del post

### Categorías y Tags

Para cada categoría o tag, el sistema:
1. Busca por nombre (`GET /categories?search=nombre`)
2. Si existe, usa su ID
3. Si no existe, lo crea (`POST /categories` o `/tags`)

### Actualización Post-Publicación

**Endpoint**: `POST /wp-json/wp/v2/posts/{id}`

Después de publicar, actualiza el contenido para insertar la URL real de WordPress en los botones de compartir (Facebook, X, WhatsApp).

## Infraestructura WordPress

| Componente | Detalle |
|-----------|---------|
| Hosting | GreenGeeks |
| PHP | 8.2 |
| Tema | Newsup (Themeansar) |
| Plugin RSS | Featured Images in RSS |
| Plugin suscripción | MC4WP (Mailchimp) |
| XML-RPC | Bloqueado |

## Notas Importantes

- Los slugs de categorías auto-creadas pueden diferir del nombre esperado (ej: `politica-2` en vez de `politica`)
- Los menús de WordPress deben apuntar al slug real, no al asumido
- La URL del sitio debe incluir `https://`; `http://` causa error 401
