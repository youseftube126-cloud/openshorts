import time
import threading
from datetime import datetime

scheduled_jobs = []

def add_to_schedule(video_path, metadata, publish_time_utc):
    scheduled_jobs.append({
        "video_path": video_path,
        "metadata": metadata,
        "publish_time": datetime.fromisoformat(publish_time_utc),
        "status": "pending"
    })

def scheduler_worker(upload_function):
    while True:
        now = datetime.now(datetime.fromisoformat("2024-01-01T00:00:00+00:00").tzinfo)
        for job in scheduled_jobs:
            if job["status"] == "pending" and now >= job["publish_time"]:
                try:
                    upload_function(job["video_path"], job["metadata"]["best_titles"][0], job["metadata"]["best_hashtags"])
                    job["status"] = "published"
                except Exception as e:
                    print(f"Publish failed: {e}")
                    job["status"] = "failed"
        time.sleep(60)

def start_scheduler(upload_function):
    threading.Thread(target=scheduler_worker, args=(upload_function,), daemon=True).start()