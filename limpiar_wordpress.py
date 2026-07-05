"""
NeuroDiario - Limpieza total de WordPress (empezar de cero)

Borra PERMANENTEMENTE todos los posts (borradores y publicados) y todos
los medios (imágenes) de la biblioteca, vía la API REST de WordPress.

Usa /wp-json/wp/v2/ con HTTPBasicAuth (GreenGeeks bloquea XML-RPC).
Lee las credenciales desde settings (variables de entorno de Railway).

SEGURIDAD (3 capas):
  1. Por defecto DRY-RUN: cuenta y reporta, no borra nada.
  2. Requiere --apply para borrar de verdad.
  3. Con --apply, pide escribir la palabra BORRAR para confirmar.

Borrado permanente: usa ?force=true (no van a la papelera).

Uso:
    python limpiar_wordpress.py            → simulación (no borra)
    python limpiar_wordpress.py --apply    → borra permanente (pide confirmación)
"""

import sys
import time
import requests
from requests.auth import HTTPBasicAuth


def _get_settings():
    from neurodiario.config.settings import settings
    return settings


def _count_items(wp_base, auth, endpoint):
    """Cuenta cuántos items hay usando el header X-WP-Total."""
    url = f"{wp_base}/wp-json/wp/v2/{endpoint}"
    try:
        r = requests.get(url, auth=auth, params={"per_page": 1, "status": "any"} if endpoint == "posts" else {"per_page": 1}, timeout=15)
        if r.status_code == 200:
            return int(r.headers.get("X-WP-Total", 0))
        # algunos hosts no aceptan status=any sin permisos; reintentar simple
        r = requests.get(url, auth=auth, params={"per_page": 1}, timeout=15)
        return int(r.headers.get("X-WP-Total", 0))
    except Exception as e:
        print(f"  ⚠ No se pudo contar {endpoint}: {e}")
        return -1


def _delete_all(wp_base, auth, endpoint, label):
    """
    Borra todos los items de un endpoint (posts o media) de forma permanente.
    Recorre en páginas hasta que no queden.
    """
    deleted = 0
    errors = 0
    url_list = f"{wp_base}/wp-json/wp/v2/{endpoint}"

    while True:
        params = {"per_page": 50}
        if endpoint == "posts":
            params["status"] = "any"
        try:
            r = requests.get(url_list, auth=auth, params=params, timeout=20)
            if r.status_code != 200:
                # fallback sin status
                r = requests.get(url_list, auth=auth, params={"per_page": 50}, timeout=20)
            items = r.json()
        except Exception as e:
            print(f"  ⚠ Error listando {endpoint}: {e}")
            break

        if not items or not isinstance(items, list):
            break

        for item in items:
            item_id = item.get("id")
            if not item_id:
                continue
            del_url = f"{wp_base}/wp-json/wp/v2/{endpoint}/{item_id}"
            try:
                dr = requests.delete(del_url, auth=auth, params={"force": "true"}, timeout=20)
                if dr.status_code in (200, 410):
                    deleted += 1
                    if deleted % 25 == 0:
                        print(f"    {label}: {deleted} borrados...")
                else:
                    errors += 1
            except Exception:
                errors += 1
            time.sleep(0.1)  # no saturar GreenGeeks

    print(f"    {label}: {deleted} borrados ({errors} errores)")
    return deleted


def run(apply_changes: bool = False):
    settings = _get_settings()
    wp_base = settings.WORDPRESS_URL.rstrip("/")
    auth = HTTPBasicAuth(settings.WORDPRESS_USER, settings.WORDPRESS_PASSWORD)

    mode = "BORRADO REAL (permanente)" if apply_changes else "SIMULACIÓN (dry-run, no borra nada)"
    print("\n" + "=" * 64)
    print("  LIMPIEZA TOTAL DE WORDPRESS")
    print(f"  Sitio: {wp_base}")
    print(f"  Modo: {mode}")
    print("=" * 64)

    n_posts = _count_items(wp_base, auth, "posts")
    n_media = _count_items(wp_base, auth, "media")

    print("\n  Contenido actual:")
    print(f"    Posts  (entradas): {n_posts}")
    print(f"    Media  (imágenes): {n_media}")

    if not apply_changes:
        print("\n  (simulación) No se borró nada.")
        print("  Para borrar de verdad, corre:  python limpiar_wordpress.py --apply")
        print("=" * 64 + "\n")
        return

    print("\n  ⚠  ESTO BORRARÁ PERMANENTEMENTE TODOS LOS POSTS E IMÁGENES.")
    print("  ⚠  No van a la papelera. NO se puede deshacer.")
    respuesta = input("\n  Para confirmar, escribe la palabra BORRAR y presiona Enter: ").strip()

    if respuesta != "BORRAR":
        print("\n  ✗ Confirmación incorrecta. No se borró nada.")
        print("=" * 64 + "\n")
        return

    print("\n  Borrando posts...")
    _delete_all(wp_base, auth, "posts", "Posts")

    print("\n  Borrando medios (imágenes)...")
    _delete_all(wp_base, auth, "media", "Media")

    print("\n  ✓ WordPress limpio. Listo para empezar de cero.")
    print("=" * 64 + "\n")


if __name__ == "__main__":
    apply_flag = "--apply" in sys.argv
    run(apply_changes=apply_flag)
