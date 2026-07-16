from datetime import datetime, timezone
from typing import Any, Dict, Optional
import logging

from app.core.mongo import get_database

logger = logging.getLogger(__name__)


async def write_audit_log(
    actor_user_id: Optional[str],
    entity_type: str,
    entity_id: str,
    action: str,
    before: Optional[Dict[str, Any]] = None,
    after: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Write an audit log entry.

    Args:
        actor_user_id: User ID performing the action (None for system actions)
        entity_type: Type of entity (lead, site, brief, asset, etc.)
        entity_id: Unique identifier for the entity
        action: Action performed (create, update, delete, download, refine, etc.)
        before: State before the action (optional)
        after: State after the action (optional)
        metadata: Additional context (IP address, asset URL, file size, etc.)
    """
    database = get_database()
    if database is None:
        # Fallback to logging if database not available
        logger.warning(
            f"Audit log (no DB): user={actor_user_id} entity={entity_type}:{entity_id} "
            f"action={action} metadata={metadata}"
        )
        return

    try:
        await database["audit_logs"].insert_one(
            {
                "actorUserId": actor_user_id,
                "entityType": entity_type,
                "entityId": entity_id,
                "action": action,
                "before": before,
                "after": after,
                "metadata": metadata or {},
                "createdAt": datetime.now(timezone.utc),
            }
        )
    except Exception as exc:
        # Never fail the main operation due to audit logging
        logger.error(f"Failed to write audit log: {exc}", exc_info=True)


async def write_asset_audit_log(
    actor_user_id: Optional[str],
    lead_id: str,
    asset_url: str,
    action: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Convenience method for asset-related audit logs."""
    await write_audit_log(
        actor_user_id=actor_user_id,
        entity_type="asset",
        entity_id=lead_id,
        action=action,
        metadata={
            "assetUrl": asset_url,
            **(metadata or {}),
        },
    )


async def write_brief_audit_log(
    actor_user_id: Optional[str],
    lead_id: str,
    action: str,
    before: Optional[Dict[str, Any]] = None,
    after: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Convenience method for brief-related audit logs."""
    await write_audit_log(
        actor_user_id=actor_user_id,
        entity_type="brief",
        entity_id=lead_id,
        action=action,
        before=before,
        after=after,
        metadata=metadata,
    )

