import requests

from flask import current_app


class BackendClient:
    @staticmethod
    def create_task(
        code, language, cpu_limit=1.0, memory_limit='256m', timeout=30
    ):
        url = f"{current_app.config['BACKEND_URL']}/api/v1/tasks"
        payload = {
            "code": code,
            "language": language,
            "cpu_limit": cpu_limit,
            "memory_limit": memory_limit,
            "timeout": timeout
        }
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()["task_id"]


    @staticmethod
    def get_task(task_id):
        url = f"{current_app.config['BACKEND_URL']}/api/v1/tasks/{task_id}"
        response = requests.get(url)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()


    @staticmethod
    def get_task_log(task_id):
        url = f"{current_app.config['BACKEND_URL']}/api/v1/tasks/{task_id}/logs"
        response = requests.get(url)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()["url"]


    @staticmethod
    def get_task_metrics(task_id):
        url = f"{current_app.config['BACKEND_URL']}/api/v1/tasks/{task_id}/metrics"
        response = requests.get(url)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

    @staticmethod
    def get_task_stream(task_id):
        url = f"{current_app.config['BACKEND_URL']}/api/v1/tasks/{task_id}/stream"
        def generate():
            with requests.get(url, stream=True) as r:
                for line in r.iter_lines():
                    if line:
                        yield line.decode('utf-8') + '\n'
        return current_app.response_class(
            generate(), mimetype='text/event-stream'
        )

