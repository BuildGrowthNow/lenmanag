# Clean Up Old Failed Jobs

## Current Situation

The dashboard shows a failed job from **May 31, 2026** with error:
```
name '_same_origin' is not defined
```

This is **stale data** - the error was from before the function was properly defined. There are:
- **1 total failed job** in the database (from May 31st)
- **0 failed jobs since July 1st**

The error has been fixed and is not recurring.

## Options to Clean Up

### Option 1: Delete Old Failed Jobs (Recommended)

Delete failed jobs older than 30 days to keep the dashboard clean:

```bash
ssh -i C:\Users\smikl\.ssh\lenquant.pem ubuntu@ec2-32-194-123-142.compute-1.amazonaws.com

# Run cleanup
docker exec lenquant-backend-1 python -c "
import asyncio
from app.core.mongo import get_database
from datetime import datetime, timezone, timedelta

async def cleanup():
    db = get_database()
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    result = await db['jobs'].delete_many({
        'status': 'failed',
        'updatedAt': {'\\$lt': cutoff}
    })
    print(f'Deleted {result.deleted_count} old failed jobs')

asyncio.run(cleanup())
"
```

### Option 2: Mark Old Failed Jobs as Archived

Keep them for records but don't show in dashboard:

```bash
docker exec lenquant-backend-1 python -c "
import asyncio
from app.core.mongo import get_database
from datetime import datetime, timezone, timedelta

async def archive():
    db = get_database()
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    result = await db['jobs'].update_many(
        {
            'status': 'failed',
            'updatedAt': {'\\$lt': cutoff}
        },
        {'\\$set': {'status': 'archived_failed'}}
    )
    print(f'Archived {result.modified_count} old failed jobs')

asyncio.run(archive())
"
```

Then update `apps/backend/app/core/leads.py` to exclude archived jobs from the dashboard query.

### Option 3: Do Nothing

The error is harmless and shows this is an old issue. As new jobs run, this will eventually scroll off the "Recent job failures" list (which currently shows the 8 most recent failures).

## Recommended Action

**Run Option 1** to delete jobs older than 30 days. This keeps your dashboard clean and removes stale error data that's no longer relevant.

After running the cleanup, refresh the dashboard and the error should disappear.
