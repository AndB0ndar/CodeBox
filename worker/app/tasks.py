import time
import threading

from io import BytesIO
from datetime import datetime

from .core.config import config
from .core.mongo import mongodb
from .core.docker_client import get_docker_client
from .core.minio_client import get_minio_client


def collect_stats(container, stats_dict, stop_event):
    try:
        stats_stream = container.stats(stream=True, decode=True)
        
        for stats in stats_stream:
            if stop_event.is_set():
                break

            cpu_stats = stats.get('cpu_stats', {})
            precpu_stats = stats.get('precpu_stats', {})

            cpu_usage = cpu_stats.get('cpu_usage', {})
            precpu_usage = precpu_stats.get('cpu_usage', {})
            
            cpu_delta = cpu_usage.get('total_usage', 0) - precpu_usage.get('total_usage', 0)
            system_delta = cpu_stats.get('system_cpu_usage', 0) - precpu_stats.get('system_cpu_usage', 0)
            
            if system_delta > 0 and cpu_delta > 0:
                num_cpus = len(cpu_usage.get('percpu_usage', [1]))
                cpu_percent = (cpu_delta / system_delta) * 100.0 * num_cpus
            else:
                cpu_percent = 0.0

            memory_stats = stats.get('memory_stats', {})
            memory_usage = memory_stats.get('usage', 0)
            memory_limit = memory_stats.get('limit', 1)
            memory_percent = (memory_usage / memory_limit) * 100.0 if memory_limit > 0 else 0.0

            stats_dict['max_cpu'] = max(stats_dict.get('max_cpu', 0), cpu_percent)
            stats_dict['max_memory'] = max(stats_dict.get('max_memory', 0), memory_usage)
            stats_dict['max_memory_percent'] = max(stats_dict.get('max_memory_percent', 0), memory_percent)

            stats_dict['cpu_sum'] = stats_dict.get('cpu_sum', 0) + cpu_percent
            stats_dict['memory_sum'] = stats_dict.get('memory_sum', 0) + memory_usage
            stats_dict['count'] = stats_dict.get('count', 0) + 1

    except Exception as e:
        print(f"Stats collection error: {e}")
    finally:
        pass


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
    stats_dict = {}
    stats_thread = None
    stop_event = threading.Event()

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

        stats_thread = threading.Thread(target=collect_stats, args=(container, stats_dict, stop_event))
        stats_thread.start()

        result = container.wait()
        exit_code = result['StatusCode']

        logs = container.logs(stdout=True, stderr=True)
        logs_buffer.write(logs)

    except Exception as e:
        exit_code = -1
        logs_buffer.write(f"Error running container: {str(e)}".encode())
    finally:
        if stats_thread and stats_thread.is_alive():
            stop_event.set()
            stats_thread.join(timeout=2)
        if container:
            container.remove()

    if stats_dict.get('count', 0) > 0:
        stats_dict['avg_cpu'] = stats_dict['cpu_sum'] / stats_dict['count']
        stats_dict['avg_memory'] = stats_dict['memory_sum'] / stats_dict['count']
        stats_dict.pop('cpu_sum', None)
        stats_dict.pop('memory_sum', None)
        stats_dict.pop('count', None)

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
        "metrics": stats_dict if stats_dict else None,
    }
    mongodb.db.tasks.update_one({"_id": task_id}, {"$set": update_data})
    print(f"Task {task_id} finished with exit code {exit_code}")

