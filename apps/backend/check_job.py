import asyncio
from app.core.leads import lead_repository


async def test():
    job_id = "cd1784dea3274ec8a9d424be3b6f0b1c"
    job = await lead_repository.get_job(job_id)
    if job:
        print("Job status:", job.status)
        print("Job progress:", job.progress)
        print("Job step:", job.step)
        print("Job error:", job.errorMessage)
    else:
        print("Job not found")


asyncio.run(test())
