from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.core.mongo import get_database


async def write_audit_log(
    actor_user_id: Optional[str],
    entity_type: str,
    entity_id: str,
    action: str,
    before: Optional[Dict[str, Any]] = None,
    after: Optional[Dict[str, Any]] = None,
) -> None:
    database = get_database()
    if database is None:
        return
    await database["audit_logs"].insert_one(
        {
            "actorUserId": actor_user_id,
            "entityType": entity_type,
            "entityId": entity_id,
            "action": action,
            "before": before,
            "after": after,
            "createdAt": datetime.now(timezone.utc),
        }
    )

