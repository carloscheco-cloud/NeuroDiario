"""
Selector inteligente de recursos multimedia.

Este módulo decide qué imagen reutilizar desde media_assets.
No busca en internet.
No descarga imágenes.
No publica.
Solo selecciona assets aprobados y activos.
"""

from typing import Optional

from neurodiario.media.library import find_best_asset, mark_asset_used


def select_featured_image(
    *,
    entity_name: Optional[str] = None,
    topic: Optional[str] = None,
    mark_used: bool = False,
) -> Optional[dict]:
    """
    Selecciona una imagen destacada aprobada para una entidad o tema.

    Prioridad:
    1. Buscar por entidad exacta/aproximada.
    2. Buscar por tema.
    3. Si no hay match, devolver None.
    """

    asset = None

    if entity_name:
        asset = find_best_asset(
            entity_name=entity_name,
            media_type="image",
            usage_type="featured_image",
            approved_only=True,
        )

    if not asset and topic:
        asset = find_best_asset(
            topic=topic,
            media_type="image",
            usage_type="featured_image",
            approved_only=True,
        )

    if not asset:
        return None

    if mark_used:
        mark_asset_used(asset.id)

    return {
        "id": asset.id,
        "entity_name": asset.entity_name,
        "entity_type": asset.entity_type,
        "topic": asset.topic,
        "source_provider": asset.source_provider,
        "source_url": asset.source_url,
        "wordpress_media_id": asset.wordpress_media_id,
        "wordpress_url": asset.wordpress_url,
        "priority": asset.priority,
        "quality_score": asset.quality_score,
        "usage_count": asset.usage_count,
    }
