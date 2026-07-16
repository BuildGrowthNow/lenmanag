"""Checkpointing system for long-running tasks.

Provides resume capability for tasks that might fail mid-execution.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.core.mongo import get_database

logger = logging.getLogger(__name__)


class TaskCheckpoint:
    """Manages checkpoints for long-running tasks."""

    def __init__(self, task_id: str, task_type: str):
        """Initialize checkpoint manager.

        Args:
            task_id: Unique identifier for the task (usually job_id)
            task_type: Type of task (extraction, generation, etc.)
        """
        self.task_id = task_id
        self.task_type = task_type

    async def save_checkpoint(
        self,
        stage: str,
        progress: int,
        state: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Save a checkpoint for the current task.

        Args:
            stage: Current stage of the task (e.g., "crawling", "enriching", "generating")
            progress: Progress percentage (0-100)
            state: State data needed to resume from this point
            metadata: Additional context
        """
        database = get_database()
        if database is None:
            logger.warning(
                f"Cannot save checkpoint for {self.task_id}: database not available"
            )
            return

        checkpoint_doc = {
            "taskId": self.task_id,
            "taskType": self.task_type,
            "stage": stage,
            "progress": progress,
            "state": state,
            "metadata": metadata or {},
            "createdAt": datetime.now(timezone.utc),
            "expiresAt": datetime.now(timezone.utc).replace(
                hour=23, minute=59, second=59
            ),  # Expire at end of day
        }

        try:
            # Upsert checkpoint (replace if exists)
            await database["task_checkpoints"].update_one(
                {"taskId": self.task_id},
                {"$set": checkpoint_doc},
                upsert=True,
            )
            logger.info(
                f"Saved checkpoint for {self.task_id} at stage '{stage}' ({progress}%)"
            )
        except Exception as exc:
            # Never fail the task due to checkpointing
            logger.error(
                f"Failed to save checkpoint for {self.task_id}: {exc}", exc_info=True
            )

    async def load_checkpoint(self) -> Optional[Dict[str, Any]]:
        """Load the most recent checkpoint for this task.

        Returns:
            Checkpoint data if found, None otherwise
        """
        database = get_database()
        if database is None:
            return None

        try:
            doc = await database["task_checkpoints"].find_one({"taskId": self.task_id})
            if doc:
                logger.info(
                    f"Loaded checkpoint for {self.task_id} at stage '{doc.get('stage')}'"
                )
                return doc
            return None
        except Exception as exc:
            logger.error(
                f"Failed to load checkpoint for {self.task_id}: {exc}", exc_info=True
            )
            return None

    async def delete_checkpoint(self) -> None:
        """Delete checkpoint after successful task completion."""
        database = get_database()
        if database is None:
            return

        try:
            await database["task_checkpoints"].delete_one({"taskId": self.task_id})
            logger.info(f"Deleted checkpoint for {self.task_id}")
        except Exception as exc:
            logger.error(
                f"Failed to delete checkpoint for {self.task_id}: {exc}", exc_info=True
            )

    @staticmethod
    async def ensure_indexes() -> None:
        """Ensure database indexes for checkpoints collection."""
        database = get_database()
        if database is None:
            return

        try:
            # Index for task lookup
            await database["task_checkpoints"].create_index("taskId", unique=True)

            # TTL index for automatic cleanup (expires at end of day)
            await database["task_checkpoints"].create_index(
                "expiresAt",
                expireAfterSeconds=0,
            )
            logger.info("Created checkpoint indexes")
        except Exception as exc:
            logger.error(f"Failed to create checkpoint indexes: {exc}", exc_info=True)


async def resume_or_start_task(
    task_id: str,
    task_type: str,
    default_start_stage: str,
) -> tuple[str, int, Dict[str, Any]]:
    """Check for existing checkpoint and resume, or start fresh.

    Args:
        task_id: Task identifier
        task_type: Type of task
        default_start_stage: Stage to start from if no checkpoint exists

    Returns:
        Tuple of (stage, progress, state)
    """
    checkpoint = TaskCheckpoint(task_id, task_type)
    existing = await checkpoint.load_checkpoint()

    if existing:
        # Resume from checkpoint
        stage = existing.get("stage", default_start_stage)
        progress = existing.get("progress", 0)
        state = existing.get("state", {})
        logger.info(f"Resuming task {task_id} from stage '{stage}' at {progress}%")
        return stage, progress, state
    else:
        # Start fresh
        logger.info(f"Starting task {task_id} from stage '{default_start_stage}'")
        return default_start_stage, 0, {}
