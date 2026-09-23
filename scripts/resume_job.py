import asyncio
import os
from app.infrastructure.queue.tasks import finalize_pipeline_task

async def main():
    job_id = "job_b3ac4b85"
    document_id = "Ch05 Marginalised Groups and_694b"
    
    # Resolving absolute path to outputs directory (using hardcoded root for safety)
    output_dir = r"C:\Users\Sanyami Jain\Documents\Vidoe_Automation\olympiad-ai-video\outputs_v3\Ch05 Marginalised Groups and_694b"
    
    print(f"Resuming pipeline for job {job_id} at {output_dir}...")
    try:
        await finalize_pipeline_task(job_id, document_id, output_dir)
        print("Successfully recovered and generated the video!")
    except Exception as e:
        print(f"Failed to recover: {e}")

if __name__ == "__main__":
    asyncio.run(main())
