import time

from io import BytesIO
from datetime import datetime

from .core.config import config
from .core.mongo import mongodb
from .core.docker_client import get_docker_client
from .core.minio_client import get_minio_client


def run_task(task_id: str):
    if mongodb.client is None:
        from .core.mongo import connect_to_mongo
        connect_to_mongo()

    docker_client = get_docker_client()
    minio_client = get_minio_client()

    task = mongodb.db.tasks.find_one({"_id": task_id})
    if not task:
        print(f"Task {task_id} not found")
        return

    mongodb.db.tasks.update_one(
        {"_id": task_id},
        {"$set": {"status": "running", "started_at": datetime.utcnow()}}
    )

    code = task['code']
    language = task['language']

    if language == 'python':
        image = 'python:3.10-slim'
        command = ['python', '-c', 'import os; exec(os.environ["CODE"])']
    elif language == 'javascript':
        image = 'node:18-slim'
        command = ['node', '-e', 'eval(process.env.CODE)']
    elif language == 'bash':
        image = 'bash:5'
        command = ['bash', '-c', 'eval "$CODE"']
    else:
        mongodb.db.tasks.update_one(
            {"_id": task_id},
            {"$set": {"status": "failed", "finished_at": datetime.utcnow()}}
        )
        return

    container = None
    logs_buffer = BytesIO()
    try:
        container = docker_client.containers.run(
            image=image,
            command=command,
            environment={'CODE': code},
            detach=True,
            stdout=True,
            stderr=True,
            remove=False,
        )
        result = container.wait()
        exit_code = result['StatusCode']

        logs = container.logs(stdout=True, stderr=True)
        logs_buffer.write(logs)
    except Exception as e:
        exit_code = -1
        logs_buffer.write(f"Error running container: {str(e)}".encode())
    finally:
        if container:
            container.remove()

    logs_buffer.seek(0)
    object_name = f"tasks/{task_id}.log"
    try:
        minio_client.put_object(
            bucket_name=config.MINIO_BUCKET,
            object_name=object_name,
            data=logs_buffer,
            length=logs_buffer.getbuffer().nbytes,
            content_type="text/plain"
        )
        logs_object = object_name
        logs_size = logs_buffer.getbuffer().nbytes
    except Exception as e:
        print(f"Failed to upload logs to MinIO: {e}")
        logs_object = None
        logs_size = 0

    update_data = {
        "status": "completed" if exit_code == 0 else "failed",
        "finished_at": datetime.utcnow(),
        "exit_code": exit_code,
        "logs_object": logs_object,
        "logs_size": logs_size,
    }
    mongodb.db.tasks.update_one({"_id": task_id}, {"$set": update_data})
    print(f"Task {task_id} finished with exit code {exit_code}")

