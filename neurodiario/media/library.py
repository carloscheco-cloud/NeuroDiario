"""
Biblioteca multimedia inteligente de NeuroDiario.

Primera fase:
- Registrar recursos multimedia.
- Buscar recursos aprobados por entidad o tema.
- Marcar recursos como usados.
"""

from datetime import datetime
from typing import Optional

from neurodiario.db.database import get_db
from neurodiario.db.models import MediaAsset


def register_media_asset(
    *,
    entity_name: Optional[str] = None,
    entity_type: Optional[str] = None,
    topic: Optional[str] = None,
    context: Optional[str] = None,
    media_type: str = "image",
    usage_type: Optional[str] = None,
    source_provider: Optional[str] = None,
    source_url: Optional[str] = None,
    local_path: Optional[str] = None,
    wordpress_media_id: Optional[int] = None,
    wordpress_url: Optional[str] = None,
    priority: int = 50,
    quality_score: float = 0.0,
    is_approved: bool = False,
    notes: Optional[str] = None,
    extra_metadata: Optional[dict] = None,
) -> MediaAsset:
    """
    Registra un recurso multimedia reutilizable.
    """

    with get_db() as db:
        asset = MediaAsset(
            entity_name=entity_name,
            entity_type=entity_type,
            topic=topic,
            context=context,
            media_type=media_type,
            usage_type=usage_type,
            source_provider=source_provider,
            source_url=source_url,
            local_path=local_path,
            wordpress_media_id=wordpress_media_id,
            wordpress_url=wordpress_url,
            priority=priority,
            quality_score=quality_score,
            is_approved=is_approved,
            extra_metadata=extra_metadata or {},
            notes=notes,
        )
        db.add(asset)
        db.flush()
        db.refresh(asset)
        db.expunge(asset)
        return asset


def find_best_asset(
    *,
    entity_name: Optional[str] = None,
    topic: Optional[str] = None,
    media_type: str = "image",
    usage_type: Optional[str] = None,
    approved_only: bool = True,
) -> Optional[MediaAsset]:
    """
    Busca el mejor recurso disponible según prioridad, calidad y menor uso.
    """

    with get_db() as db:
        query = db.query(MediaAsset).filter(
            MediaAsset.is_active == True,  # noqa: E712
            MediaAsset.media_type == media_type,
        )

        if approved_only:
            query = query.filter(MediaAsset.is_approved == True)  # noqa: E712

        if entity_name:
            query = query.filter(MediaAsset.entity_name.ilike(f"%{entity_name.strip()}%"))

        if topic:
            query = query.filter(MediaAsset.topic.ilike(f"%{topic.strip()}%"))

        if usage_type:
            query = query.filter(MediaAsset.usage_type == usage_type)

        asset = (
            query.order_by(
                MediaAsset.priority.desc(),
                MediaAsset.quality_score.desc(),
                MediaAsset.usage_count.asc(),
                MediaAsset.created_at.desc(),
            )
            .first()
        )

        if asset:
            db.expunge(asset)

        return asset


def mark_asset_used(asset_id: int) -> bool:
    """
    Incrementa el contador de uso de un recurso multimedia.
    """

    with get_db() as db:
        asset = db.query(MediaAsset).filter(MediaAsset.id == asset_id).first()
        if not asset:
            return False

        asset.usage_count = (asset.usage_count or 0) + 1
        asset.last_used_at = datetime.utcnow()
        asset.updated_at = datetime.utcnow()
        return True
